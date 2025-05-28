#!/usr/bin/env python3
import os
import glob
import markdown
from invoke import task, run

INCLUDE_PROJECTS  = [
    "pact-conformance-service",
    "pact-directory-service",
    "data-exchange-protocol",
    "tr"
]
IGNORE_FILES = [
    "EDITING.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "LICENSE.md"
]

# Generate html from markdown
def render_markdown(input, output: str):
    """
    Render a markdown file to HTML.
    Args:
        input (str): The input markdown file.
        output (str): The output HTML file.
    """
    rel_root_path = (output.count('/')-1) * "../"
    header = f"""<!doctype html>
<html lang="en">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type"><html>
    <link href="{rel_root_path}assets/markdown.css" rel="stylesheet" />
</head>
<body>
    """
    footer = """</body>
</html>"""
    with open(input, "r") as input_file:
        html = header + markdown.markdown(
            input_file.read(), 
            extensions=['tables','md_in_html', 'fenced_code', 'codehilite', 'toc', 'attr_list']
            ) + footer
        
        # replace all <a href="... .md" to <a href="... .html"
        html = html.replace('.md"', '.html"')
        
        with open(output, "w") as output_file:
            output_file.write(html)

def render_markdown_dir(input_dir, output_dir):
    """
    Render all markdown files in a directory to HTML files in the output directory.
    Args:
        input_dir (str): The directory containing markdown files.
        output_dir (str): The directory where HTML files will be saved.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Find all files in the input directory recursively
    input_paths = glob.glob(f"{input_dir}/**/*", recursive=True)

    for input_path in input_paths:
        relative_path = os.path.relpath(input_path, input_dir)
        output_path = os.path.join(output_dir, relative_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if not os.path.isfile(input_path):
            continue
        if output_path.endswith(".md"):
            output_path = output_path[:-3] + ".html"
            print(f"Rendering {input_path} to {output_path}")
            render_markdown(input_path, output_path)
        else:
            run(f'cp "{input_path}" "{output_path}"')

def copy_and_adjust_links(input_file, output_file):
    """
    Adjust links in markdown files to point to the correct HTML files.
    Args:
        input_file (str): The input markdown file.
        output_file (str): The output markdown file with adjusted links.
    """
    with open(input_file, "r") as infile:
        content = infile.read()
    # Replace any links to docs/ 
    content = content.replace('](docs/', '](')
    with open(output_file, "w") as outfile:
        outfile.write(content)

@task
def init(c):
    for repo in INCLUDE_PROJECTS:
        if not os.path.exists(f"temp/{repo}"):
            run(f"git clone --depth=1 https://github.com/wbcsd/{repo}.git temp/{repo}")
        else:
            run(f"pushd temp/{repo} && git pull && popd")
        run(f"rm -rf docs/{repo}")
        os.makedirs(f"docs/{repo}", exist_ok=True)

@task
def clean(c):
    run(f"rm -rf build")
    for repo in INCLUDE_PROJECTS:
        run(f"rm -rf docs/{repo}")

@task
def build(c):
    if not os.path.exists("temp"):
        print("Run `invoke init` first to clone the repositories.")
        return 1
    for repo in INCLUDE_PROJECTS:
        run(f"rm -rf docs/{repo}")
        os.makedirs(f"docs/{repo}", exist_ok=True)

        # Copy all content in docs directories from temp/repo to docs/repo
        if os.path.exists(f"temp/{repo}/docs"):
            run(f"cp -r temp/{repo}/docs/* docs/{repo}")

        # Selectively copy markdown files from the root of the repo to docs/repo
        # Making sure to adjust links in the markdown files
        for file in glob.glob(f"temp/{repo}/*.md"):
            if os.path.basename(file) == "README.md":
                # Special case for README files
                if not os.path.exists(f"docs/{repo}/index.md"):
                    copy_and_adjust_links(file, f"docs/{repo}/index.md")
            elif not os.path.basename(file) in IGNORE_FILES: 
                    copy_and_adjust_links(file, f"docs/{repo}/{os.path.basename(file)}")

    run(f"cp -r temp/tr/* docs/tr")
    run(f"cp -r temp/data-exchange-protocol/ref docs")
    run(f"rm docs/tr/README.md")
    run(f"rm docs/tr/index.md")

    os.makedirs("build", exist_ok=True)
    render_markdown_dir(f"docs", f"build")
    run(f"cp -r assets build")
