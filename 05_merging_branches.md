[Slides for the Lecture](https://www.canva.com/design/DAEUZEra8W0/b4I77uG1YJAu4q6UOTIG6Q/view)

[Docs for the lecture](https://git-scm.com/docs/git-merge)

# Merging Branches

## Merging

Branching makes it super easy to work within self-contained contexts, but often we want incorporate changes from branch into another!

We can do this using the <code>git merge</code> command

### Important points to remember:
* We can merge branches, not specific commits
* We always merge **to** the current HEAD branch.

### Merging made easy

To merge, follow these basic steps:
1. Switch to or checkout the branch you want to merge the changes into (the receiving branch)
2. Use the <code>git merge</code> command to merge changes from a specific branch into current branch.

To merge the *bugfix* branch into *master* branch

```bash
git switch master
git merge bugfix
```

Let's say this is current state of our branches...<br>

<img src="../src/img/branch_merge_01.png" width=400>
<p></p>

To merge the *bugfix* branch to the *master* branch, switch to *master* branch<br>

<img src="../src/img/branch_merge_02.png" width=400>
<p></p>

Now merge the *bugfix* branch to the *master* branch using <code>git merge bugfix</code> command.<br>

<img src="../src/img/branch_merge_03.png" width=400>
<p></p>
This is what it really looks like...

Remember, branches are just defined by a branch pointer

The *bugfix* branch has some additional commits that are not present in the master branch. To catch up, we just have to move forward.<br>
<img src="../src/img/branch_merge_04.png" width=400>
<p></p>

By using the <code>git merge bugfix</code> command, *master* branch will get all the history of the *bugfix* branch

<img src="../src/img/branch_merge_05.png" width=400>

This is called **Fast Forward Merge**.

After merging, the *bugfix* branch and the *master* branch won't be in sync forever. It's just once place where *master* and *bugfix* branches are together, if you commit new changes in the master branch, they won't be reflected in the *bugfix* branch and vice-versa, until you merge them again. Simple, *bugfix* is still a branch. Fast-forward merge is same as another merge, but if it is a fast-forward merge, it will be shown in the terminal as shown below.

```bash
Updating 4913056..8ee3fc1
Fast-forward
 playlist.txt | 8 +++++++-
 1 file changed, 7 insertions(+), 1 deletion(-)
```

## Generating Merge Commits

### Not all merges are fast forward

Let's assume, we made two commits in our *master* branch and created a new branch called *bugfix* branch and made two commits in the *bugfix* branch. If we merge the *bugfix* branch in *master* branch, it's a simple fast-forward merge. For this case, let's assume, we made some changes in the *master* branch after branching out the *bugfix* branch, but this branch is not conflicting with the data in the master branch.

Still we use the same process for committing, but rather than using fast-forward merge, git performs a **"merge commit"** and we will end up with a new commit in the master branch, and git will prompt you for the commit message.

### Merge Conflicts

Depending on the specific changes you are trying to merge, Git may not be able to automattically merge. This results in **merge conflicts**, which you need to manually resolve. When there is conflict, git shows something like this in the terminal...
```bash
CONFLICT (content): Merge conflict in blah.txt
Automatic merge failed; fix conflicts and then commit the result.
```

When you encounter a merge conflict, Git warns you in the console that it could not automatically merge.

**It also changes the contents of your files to indicate the conflicts that it wants you to resolve.**
```
<<<<<<<HEAD
I have 2 cats
I also have chickents
======
I used to have a dog :(
>>>>>>>bugfix
```
### Conflict Markers

* The content from your HEAD (the branch you are trying to merge content into) is displayed between **<<<<<< HEAD and =======**

* The content from the branch you are trying to merge from is displayed between the **======= and >>>>>>>** symbols

### Resolving Conflicts

Whenever you encounter merge conflicts, follow these steps to resolve them:
1. Open up the file(s) with merge conflicts
2. Edit the file(s) to remove the conflicts. Decide which branch's content you want to keep in each conflict. Or keep the content from both.
3. Remove the conflict "markers" in the document
4. Add your changes and then make a commit!

## Exercise

[Click Here](https://www.notion.so/Git-Merging-Exercise-0236a17f04c847159a38f5efa978ce2c) to view the exercise
