---
layout: post
title: "git is actually OK for (some) binaries"
date: 2015-03-04 07:52:53 -0800
comments: true
categories: git, dvcs
---

In hacker circles there's a common urban legend that it is somehow "bad" or inefficient to version binary files with git (["DVCS systems are not good candidates for storing binary files"](https://confluence.atlassian.com/display/BITBUCKET/Reduce+repository+size#Reducerepositorysize-DeletingFilesandotherMaintenance), ["Don't ever commit binary files to git"](https://robinwinslow.co.uk/2013/06/11/dont-ever-commit-binary-files-to-git/)). In one recent Hacker News post, a commenter went so far as to write ["Anyone checking in 500MB artifacts into git is almost certainly refusing to use git correctly"](https://news.ycombinator.com/item?id=9139960). While 500MB may be a little on the big side for my taste,
as long as they are the *right type* of binaries it should not be an issue.

So let's discuss the types of binaries you might consider versioning within git<sup>1</sup>.

Binary files that fit these constraints are good candidates for git versioning:

* Localized, relatively small changes between revisions (this mostly implies compressibility).
* Proportionality between source changes and resulting binary changes (ie, if the asset is produced by some process--compilation, etc--a small change in the source will result in a proportionately small change in the binary)
* &le; 150MB in size per file<sup>2</sup>

The reason these types of files work well in git is because git stores revisions as binary deltas, which are precisely what we want. In fact that's exactly how [Amazon CodeDeploy](http://aws.amazon.com/codedeploy/) and my similar open source project [Elita](https://github.com/bkeroack/elita) manage binary code deployments -- by committing compiled files into a git repository, pushing to a central repository and then git pulling in the changes on the target servers.

Let's do a little test.

I have a simple Go program that I want to compile and version in git:

```go
package main

import "fmt"

func main() {
	fmt.Printf("Hello, world!\n")
}
```

Compile it:

```bash
$ cd ~/go/src/gittest
$ go build
$ ls -lh
total 3776
-rwxr-xr-x  1 bk  staff   1.8M Mar  4 08:17 gittest
-rw-rw-r--  1 bk  staff    75B Mar  4 08:16 test.go
```

Now we'll create a git repo and check these files in. Go programs compile to native machine code so this would be similar if the program was written in C or C++.

```bash
$ git init
Initialized empty Git repository in /Users/bk/go/src/gittest/.git/
$ git add -A
$ git commit -m "initial version"
[master (root-commit) 9a381bd] initial version
 2 files changed, 7 insertions(+)
 create mode 100755 gittest
 create mode 100644 test.go
```

Now lets make a small change to our source code:

```go
package main

import "fmt"

func main() {
	fmt.Printf("Hello, Arbre!\n")
}
```

Compile, commit it:

```bash
$ go build
$ git add -A && git commit -m "second version"
[master a00b091] second version
 2 files changed, 1 insertion(+), 1 deletion(-)
```

Cool. Now let's generate a binary patch for the executable and see how big it is:

```bash
$ git diff --binary master~1:gittest gittest > ./diff.patch
$ ls -lh
total 3784
drwxr-xr-x  12 bk  staff   408B Mar  4 08:34 .git
-rw-r--r--   1 bk  staff   404B Mar  4 08:39 diff.patch
-rwxr-xr-x   1 bk  staff   1.8M Mar  4 08:34 gittest
-rw-rw-r--   1 bk  staff    75B Mar  4 08:34 test.go
```

404 bytes! Nice. Here's what it looks like:

```
diff --git a/gittest b/gittest
index 77923533b0c042ef0c45dda307bbc9c938070a87..ec7b9ebaf7c0e486a2faca8c55143824a1473016 100755
GIT binary patch
delta 107
zcmWN=w+Vni00mIYIp?s9s|YS|VsG)m)?ow}xmnKU3jc$5%j1^E2?Hi9*l^&&gO30q
mBE(PfDQ6L@*e<OSPC4V83og0hnj3Dp<DLf|d3v>)>-`7IJUHI~

delta 107
zcmWN=xe0(k00cn%|Ns0g&rlE)F*R5)wHU!hu9h<~a0lj++a<RH8gv*iVZnw27an{B
l2=C}s);=%Ocz!D4m=jJp<D3f?Tyn)VH{5c^{qw0otUue?IU4`~
```

That looks like a nice clean binary delta to me. Certainly it isn't an entire copy of the second version of the file.

Now let's check out the original version of the binary:

```bash
$ git checkout master~1 2> /dev/null
$ ./gittest
Hello, world!
```

...and apply the patch:

```bash
$ git apply ./diff.patch
$ ./gittest
Hello, Arbre!
```

As you can see the patched binary runs perfectly!

One final thing. Let's check the size of the git metadata:

```bash
$ ls -lh
total 3784
drwxr-xr-x  12 bk  staff   408B Mar  4 08:41 .git
-rw-r--r--   1 bk  staff   404B Mar  4 08:39 diff.patch
-rwxr-xr-x   1 bk  staff   1.8M Mar  4 08:42 gittest
-rw-r--r--   1 bk  staff    75B Mar  4 08:41 test.go
$ du -hs ./.git/
1.3M	./.git/
```

1.3MB is less than the size of a single copy of the original binary (likely due to compression). This proves that git is not storing our binary revisions as entire copies of the file but as much more efficient deltas.

For which types of binary files would git *not* be appropriate?

Anything where changes between revisions are scattered throughout the file--for example, anything encrypted with a modern cipher will likely be almost completely different for even the most tiny of changes to the original plain text. Similar results can occur from compression.

It will take some experimentation to see if your particular binary assets will work efficiently. Compiled executable binaries work particularly well. I've used git for both native machine code binaries and .NET CLR binaries--I haven't tested JVM binaries specifically but imagine they would be similar. Images, music, etc may also be worth experimenting with.

Thanks for reading and feel free to leave a comment with any corrections or additional info!


---

1. I say git specifically because it is relatively smart about versioning binary assets as shown in this post, versus something like Mercurial which--last I knew--simply stored binary file revisions as flat blobs of the full file.

2. This may actually be an urban legend as well. I'm not familiar with git internals but my understanding is that the binary diffing algorithm gets inefficient above this threshold. I would love to hear if that is incorrect.
