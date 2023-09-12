[Slides for this lecture](https://www.canva.com/design/DAEXMibkysc/4PgPWiQqZ5UwCxMruH6BmQ/view?utm_content=DAEXMibkysc&utm_campaign=designshare&utm_medium=link&utm_source=viewer)

---

# The Git Docs
[Click Here](https://git-scm.com/doc)

# Atomic Commits
When possible, a commit should encompass a single feature, change, or fix. In other words, try to **keep each commit focused on a single thing.**

This makes it much easier to undo or rollback changes later on. It also makes your code or project easier to review.

# Commit Messages: Present or Past Tense?

Git docs suggests to use **Present-Tense Imperative Style**.

Describe your changes in imperative mood, e.g. "make xyzzy do frotz" instead  of "[This patch] makes xyzzy do frotz" or "I changed xyzzy to do frotz", as if you are giving orders to the codebase to change its behavior.

# Escaping VIM & Configuring Git's Default Editor

Running <code>git commit</code> will commit all staged changes. It also opens up a text editor and prompts you for a commit message.

This can be overwhelming when you're starting out, so instead you can use...
> git commit -m "my message"

If you are accidentally stuck in VIM, use the following steps to add your messages and leave VIM
* Type 'i' for inserting/writing your commit message
* After writing your commit message, press 'esc' [escape button].
* Then type, ":wq" which represents write and quit.

Sometimes, you might need to write multiples lines of commit messages. In those cases, you cannot use <code>git commit -m "message"</code>, you will need some code editor to write the long commit message. For those cases, you have to configure some text editor.

[Click here](https://git-scm.com/book/en/v2/Appendix-C%3A-Git-Commands-Setup-and-Config) to check how to configure different text editors

From the above link, to configure VS Code as our default text editor, we have to use the below command
> git config --global core.editor "code --wait"
* The --wait part of the command represents that git waits until you save the commit message and closes the opened file in the editor to commit with the given message.

**Note: Unless, you have multiple lines of commit messages, you can use <code>git commit -m "my message"</code>. It is always a best practice to have brief commit messages.**

# Git Log Command

As we have previously seen, we can have long commit messages. When you have long commit messages and/or more no. of commits, it's a bit too much to look into the logs. For this, you can see brief descriptions of the logs. There are numerous options on how to view, filter, format, and do a whole lot of stuff with logs in the git docs [Click Here](https://git-scm.com/docs/git-log#_commit_formatting). But, to have a quick one line look at the logs, you can use the below command

> git log --oneline

This will show the first line of the commit messages (That's why, even though you have multiple lines of commit messages, it's a best practice to have the first line briefly describe the changes in the commit), and prefix of the commit hash, instead of showing all the 40 characters.

# Committing with a GUI

Using GitLens extension, we can add files to the staging area, commit the changes with commit messages, and also check the branches and heirarchy of the commits in a graph.
* You can add files to staging area and commit them in the Source Control Menu in VS Code present in the LHS (Or click Ctrl+Shift+G G)
* To view the graph, there are various ways. First install GitLens extension and ...
    * In VS Code, type Ctrl+Shift+P and type "Show Commit Graph", a new tab with commit graph will open.
    * You can also click in the below shown icons

        <img src="../src/img/git_graph_01.png" width="300"><br>
        <img src="../src/img/git_graph_02.png" width="300">

# Amending Commits

* Suppose you made a commit and then realized you forgot to include a file!
* Or you made a typo in a commit message that you want to correct.

Rather than making a brand new separate commit, you can 'redo' the **previous commit** using the <code>--amend</code> option.

**Note: This is only work for the previous commit, nothing before that**

## Example:
* Let's say, we have files from a.txt to j.txt.
* We added headings in a.txt, b.txt, c.txt, and d.txt.
* We want to commit that changes and used the following commands
```bash
> git status # To check if (we are in a git repo/the tree is clean/ any other files in the staging area/ changes in the other files/changes in the intended files)
> git add a.txt b.txt c.txt # And forgot to add d.txt
> git status # This will show all the files in the staging area, let's say we didn't pay attention to the d.txt file which modified and not in the staging area.
> git commit -m "add keadings" # Committing the changes with a typo in the commit message.
> git status # This will now show us that 
```
* Now, we want to change the commit message as well as add the updated (we can do any one of them or both of them) using the following commands
```bash
> git add d.txt # Adding it to the staging area
> git commit --amend # This will open the configured text editor for adding the commit message. There, you can edit the commit message, save it, and close it. If you don't want to edit the commit message, you can simply close it. But, we will be editing our commit message to "add headings" and then close it.
```
* That's it, it will add d.txt file in the previous commit and update the commit message also.

# Ignoring Files

* We can tell Git which files and directories to ignore in a given repository, using a .gitignore file.
* This is useful for files you know you NEVER want to commit, including:
    * Secrets, API keys, credentials, etc.
    * Operating System files
    * Log files
    * Dependencies & packages

## .gitignore
Create a file called ".gitignore" in the root of a repository (We can place it anywhere in the repo. But traditionally, we keep in the root of the repo). Inside the file, we can write patterns to tell Git which files & folders to ignore:
* ***.DS_Store*** will ignore files named .DS_Store (Exact file names)
* ***folderName/*** will ignore an entire directory (Folder names)
* __*.log__ will ignore any files with the .log extension (Any file with the given extension)

### Reference Links
* [Click Here](https://www.toptal.com/developers/gitignore) to the default .gitignore template for your project.
* [Click Here](https://git-scm.com/docs/gitignore) for Git Docs on Gitignore
* [Click Here](https://docs.github.com/en/get-started/getting-started-with-git/ignoring-files) for GitHub Docs on Gitignore

### Exercise
1. Create a weather app in python
2. Add the relevant files in .gitignore
List all the commands used and their explanations below
```bash
> mkdir WeatherApp # Create the root directory

> cd WeatherApp # Get into the root directory

> git status # Make sure that git is not intialized here

> git init # Initialize Git Repo

> conda create -p ./weather_env python==3.7 -y # Create a new environment in the current directory for this project

> conda activate ./weather_env # Activate the new environment

> pip install  requests pyyaml # Install the required packages

>touch main.py # Create, open, and write the required code in the file. Confining to the current task, let's not make any intermediate changes in the code.

> touch credentials.yaml # Add the weather API key from https://home.openweathermap.org

# Just created the files and installed the libraries

> git status # Check the status

# Shows no commits yet

> git add main.py

> git status

# main.py in staging area, credentials.yaml and weather_env in untracked files.

> git commit -m "create main.py"

# Adding code and credentials data

> git status # This will show that main.py as modified, and credentials and weather_env/ as untracked files.

> git add main.py # We can't use "git add .", as we don't want to add all the files

> git commit -m "add initial code"

> touch .gitignore

> start .gitignore # Add the filenames and foldernames that we don't want git to track (folder names should end with "/")

> git status # Now, we don't find credentials.txt and weather_env/ in the untracked files. We will only see .gitignore in untracked files

> git add . # Now, this will not add the files / folders mentioned in the .gitignore file.

> git commit -m "add .gitignore file"

> pip freeze > requirements.txt

> git status

> git add requirements.txt

> git status

> git commit -m "add requirements.txt"
```
We just learnt how to add filenames and foldernames by specifying the names and extensions in .gitignore. There are a lot of ways to add patterns in .gitignore files, check [git docs for gitignore](https://git-scm.com/docs/gitignore) for more information.
