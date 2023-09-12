[Slides for this lecture](https://www.canva.com/design/DAEPOwX2Zzs/90STrbMXNysYIkSsxUCu-g/view)

# Branches

<img src="../src/img/branching_01.png" width=750>

* Branches are essential part of Git. 
* They are like alternate timelines for a project.
* They enable us to create separate contexts where we can try new things, or even work on multiple ideas in parallel.
* **If we make changes on one branch, they do not impact the other branches (unless we merge the changes)**

In git we are always working on a branch. We have already seen this before...
```bash
On branch master
nothing to commit
```
## The Master Branch
* The Default branch name is **master**.
* It doesn't do anything special or have fancy powers. It's just like any other branch. (*technically that's not 100% true as we'll see later)

## Master
* Many people designate the master branch as their "source of truth" or the "official branch" for their codebase, but that is left to you to decide.
* From Git's perspective, the master branch is just like any other branch. It does not have to hold the "master copy" of your project.

## Master vs Main
In 2020, GitHub renamed the default branch from **master** to **main**. The default Git branch name is still **master**, though the Git team is exploring a potential change. (We will get back to this later.)

## HEAD

In the <code>git log</code> response, we often see **(HEAD -> master)** in the most recent commit
```bash
commit 997daa49bcfbbc278e89925acfbb12503d326ef8 (HEAD -> master)
Author: Sai <saisrinivas.samoju@gmail.com>
Date:   Wed Sep 7 16:26:26 2022 +0530

    add requirements.txt
```
HEAD is simply a pointer that refers to the current "location" in your repo. It points to a particular branch reference.

## Viewing branches

Use command <code>git branch</code> to view all the branches.

The current branch has an asterisk before it's name. eg..

```bash
*master
```

## Viewing more info

Use the **-v** flag with <code>git branch</code> to view more information about each branch.

> git branch -v


## Creating Branches

Use <code>git branch < branch-name ></code> to make a new branch **based upon the current HEAD**. (branch name should not have spaces)

This just creates the branch. It does not switch you to that branch (the HEAD stays the same)

* The latest commit will have two branches. But, the HEAD still doesn't point towards the newly created branch. Therefore, all the upcoming commits will build up the existing branch unless HEAD points towards your newly created branch.

## Switching Branches

Once you have created a new branch use <code>git switch < branch-name ></code> to switch to it.
* If you misspell the name of the new branch while switching, it will just throw up an error and nothing more.
* After switching to new branch, if you make any commits, those commits will only exist in the new branch, and not in any other branches.
* Likewise, you can create branches in the branches and so on, based on your requirements.
* If you switch to the old branch after multiple commits in the new branch, you can see the project in the stage where the last commit in the old branch is present, and if you switch to the new branch, you can see the project in the stage where the last commit in the new branch happened.

## Another way of Switching

* Historically, we used <code>git checkout < branch-name ></code> to switch branches. This still works.
> git checkout < branch-name >
* The **checkout** command does a million additional things, so the decision was made to add a standalone **switch** command which is much simpler.
* You will see older tutorials and does using checkout rather than switch. Both now work.

## Creating & Switching

* Use any of the below commands to create a new branch and switch to it using a single line
```bash
git switch -c <branch-name>
# OR
git checkout -b <branch-name>
```

## Switching Branches with Unstaged changes

* If you modify an existing file in particular branch and try to switch to the other branch without committing the changes, git will throw an error.
    * To continue switching to the other branch, you should either commit the changes in the existing branch or stash it(we will learn about stashing later.)
* If you create a new file in the existing branch and try to switch to the other branch without committing the changes, git won't throw an error. Because the new file is still and untracked file.

## Deleting and Renaming Branches

### Deleting Branches

* If you want to delete a branch, it should not be your current branch.
    * If you want to delete the current branch, you should switch to other branch and delete the branch you want to delete using the following command
    > git branch -d < branch-name >
    * If it throws an error that the branch you want to delete is not fully merged, you can force delete it using the following command
    > git branch -D < branch-name >

### Renaming Branches

* Unlike deleting a branch, if you want to delete a branch, it should be your current branch. In other words, you can rename only your current branch.
* To rename the current branch, use the following command
> git branch -m < new-branch-name >

## Exercise

[Click Here](https://www.notion.so/Branching-Exercise-b5460c881d56400cb046357d9a430bf8) to find the instructions for the exercise