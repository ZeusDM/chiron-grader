#! /usr/bin/python3

# This is a script that helps me grade homework assignemnts.

from config import template_tex
import argparse
import os
import subprocess
import random
import json
import pandas

def split(pdf_file):
    if not os.path.exists(pdf_file):
        raise Exception("File does not exist")
    directory = os.path.dirname(pdf_file)
    p = subprocess.Popen(["zathura", pdf_file])
    keep = True
    number = 0
    while keep:
        page = input("Last page: ")
        if page.isnumeric():
            page = int(page)
            total = int(subprocess.run("pdfinfo " + pdf_file + " | grep 'Pages' | awk '{print $2}'", shell=True, capture_output=True).stdout.decode("utf-8").replace("\n", ""))
            number += 1
            while os.path.exists(pdf_file.replace(".pdf", "_{:02d}.pdf".format(number))):
                number += 1
            subprocess.run(["mutool", "merge", "-o", pdf_file.replace(".pdf", "_{:02d}.pdf".format(number)), pdf_file, "1-"+str(page)])
            subprocess.run(["mutool", "merge", "-o", pdf_file, pdf_file, str(page+1)+"-"+str(total)])
        else:
            keep = False
    p.terminate()

def rename(directory):
    submissions_directory = os.path.join(directory, "files/")
    if not os.path.exists(submissions_directory):
        raise Exception("Submissions directory does not exist")
    list_pdf = [f for f in os.listdir(submissions_directory) if f.endswith(".pdf")]
    for filename in list_pdf:
        p = subprocess.Popen(["zathura", os.path.join(submissions_directory, filename)])
        new_filename = "_".join(reversed(input("Name: ").split(" "))) + ".pdf"
        p.terminate()
        subprocess.call(["mv", os.path.join(submissions_directory, filename), os.path.join(submissions_directory, new_filename)])

def grade(directory, problem):
    submissions_directory = os.path.join(directory, "files/")
    grades_directory = os.path.join(directory, "grades/")
    if not os.path.exists(submissions_directory):
        raise Exception("Submissions directory does not exist")
    if not os.path.exists(grades_directory):
        os.mkdir(grades_directory)
    list_pdf = [f for f in os.listdir(submissions_directory) if f.endswith(".pdf")]
    random.shuffle(list_pdf)
    for filename in list_pdf:
        pdf_file = os.path.join(submissions_directory, filename)
        grade_file = os.path.join(grades_directory, filename.replace(".pdf", "")+"_"+problem+".txt")
        comments_file = os.path.join(grades_directory, filename.replace(".pdf", "")+"_"+problem+"_comments.txt")
        tmp_file = os.path.join("/tmp/", filename.replace(".pdf", "")+"_"+problem+".tex")
        if not os.path.exists(grade_file):
            x = input("Continue grading? (y/n) ")
            if x != "" and x[0].lower() == "n":
                break
            p = subprocess.Popen(["zathura", pdf_file])
            with open(tmp_file, "w") as f:
                f.write("% GRADE: \n% Write comments below this line \n")
            subprocess.call(["nvim", tmp_file])
            with open(tmp_file, "r") as f:
                content = f.readlines()
            grade = content[0].replace("% GRADE:", "").replace("\n","").replace(" ", "")
            try:
                grade = str(pandas.eval(grade))
            except ValueError:
                pass
            comments = "".join(content[2:])
            if not grade.isspace() and grade != "":
                with open(grade_file, "w") as f:
                    f.write(grade)
            if not comments.isspace() and comments != "":
                with open(comments_file, "w") as f:
                    f.write(comments)
            p.terminate()

def format_grade(problem, grade, max_score):
    return("\\grade{" + problem + "}{" + grade + "}{" + max_score + "}\n")

def format_comments(comments):
    return("\\comments{" + comments + "}\n")

def export(directory):
    submissions_directory = os.path.join(directory, "files/")
    export_directory = os.path.join(directory, "export/")
    grades_directory = os.path.join(directory, "grades/")
    json_path = os.path.join(directory, "info.json")
    if not os.path.exists(submissions_directory):
        raise Exception("Submissions directory does not exist")
    if not os.path.exists(grades_directory):
        raise Exception("Grades directory does not exist")
    if not os.path.exists(json_path):
        raise Exception("info.json does not exist")
    if not os.path.exists(export_directory):
        os.mkdir(export_directory)
    for f in os.listdir(export_directory):
        os.remove(os.path.join(export_directory, f))
    with open(json_path) as f:
        y = json.load(f)
    title = y["title"]
    problems = y["problems"]
    list_pdf = [f for f in os.listdir(submissions_directory) if f.endswith(".pdf")]
    processes = []
    for filename in list_pdf:
        lastname, firstname = filename.replace(".pdf", "").split("_")
        grades = ""
        total_score = 0
        max_total_score = 0
        for problem, max_score in problems.items():
            grade_file = os.path.join(grades_directory, filename.replace(".pdf", "")+"_"+problem+".txt")
            comments_file = os.path.join(grades_directory, filename.replace(".pdf", "")+"_"+problem+"_comments.txt")
            max_total_score += max_score
            if os.path.exists(grade_file):
                with open(grade_file) as f:
                    grade = f.read()
                grades += format_grade(problem, grade, str(max_score))
                total_score += int(grade)
                if os.path.exists(comments_file):
                    with open(comments_file) as f:
                        comments = f.read()
                    grades += format_comments(comments)
            else:
                grades += format_grade(problem, "not graded", str(max_score))
        tex_file = os.path.join(export_directory, filename.replace(".pdf", "")+"_grades.tex")
        with open(template_tex) as f:
            tex = f.read()
        replace_dict = {"TITLE": title, "FIRSTNAME": firstname, "LASTNAME": lastname, "SCORE": str(total_score), "MAX": str(max_total_score), "PERCENTAGE": str((100*total_score) // max_total_score + ((100*total_score) % max_total_score > 0)), "GRADES": grades}
        for key, value in replace_dict.items():
            tex = tex.replace(key, value)
        with open(tex_file, "w") as f:
            f.write(tex)
        processes.append(subprocess.Popen(["pdflatex", "-halt-on-error", "-output-directory", export_directory, tex_file]))
    for p in processes:
        p.wait()
    for f in os.listdir(export_directory):
        if not f.endswith(".pdf"):
            os.remove(os.path.join(export_directory, f))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Grader helper')
    subparser = parser.add_subparsers(dest='command')
    rename_subparser = subparser.add_parser('rename')
    rename_subparser.add_argument('--directory', type=str, default=".")
    grade_subparser = subparser.add_parser('grade')
    grade_subparser.add_argument('--directory', type=str, default=".")
    grade_subparser.add_argument('--problem', type=str, required=True)
    export_subparser = subparser.add_parser('export')
    export_subparser.add_argument('--directory', type=str, default=".")
    split_subparser = subparser.add_parser('split')
    split_subparser.add_argument('file', type=str)
    args = parser.parse_args()
    if args.command == 'rename':
        directory = os.path.abspath(os.path.expanduser(os.path.expandvars(args.directory)))
        rename(directory)
    elif args.command == 'grade':
        directory = os.path.abspath(os.path.expanduser(os.path.expandvars(args.directory)))
        grade(directory, args.problem)
    elif args.command == 'export':
        directory = os.path.abspath(os.path.expanduser(os.path.expandvars(args.directory)))
        export(directory)
    elif args.command == 'split':
        file = os.path.abspath(os.path.expanduser(os.path.expandvars(args.file)))
        split(file)
    else:
        parser.print_help()
