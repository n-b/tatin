# Tatin

## Create git clones of opensource.apple.com

Apple isn’t really famous for its contributions to open source projects: its latest major effort was [Mac OS forge](http://www.macosforge.org). As the name implies, it dates from when sourceforge was cool.

On the other hand, Apple publishes the code ot the opensource components it uses at [opensource.apple.com](http://opensource.apple.com). I wrote a small script that scrapes the projects metadata, downloads all the tarballs and recreates git repositories at [github.com/unofficial-opensource-apple](http://github.com/unofficial-opensource-apple).

![](objc4.png)

Apple releases opensource code for four _Products_: **Developer Tools**, **OS X**, **OS X Server** and **iOS**. For every _Release_ of these products, they (in theory) also publish the sourcecode of the _Version_ of the opensource _Project_.

There are 509 projects in total. Some are never actually referenced in a Product. (Like DarwinInstaller, of course, or zsh, unfortunately.) The source code is made available as tarballs for each version, 5334 in total.

`tatin.py` attempts to recreate a more usable git repository for each of these projects:

* It downloads all the version tarballs of this project, 
	* Creates a new commit for each version
	* Adds tags for each Product Release referencing this version.
	* The `Modified-At` header returned by opensource.apple.com when requesting the tarballs is _relatively_ coherent after 2010. (The epoch of opensource.apple.com seems to be the 5th of February 2009.) This date is used as the `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE`.
	* Additionally, the git user is set to `opensource.apple.com`. (A nice side effect of overriding the git commiter/author and the commit/author dates is that the commit hashes stay identical when a repository is recreated from scratch.)
* Creates a repository at `github.com/unofficial-opensource-apple/<project>`

**Warning**: it’s written in Python, a language in which I am a total noob. Basically, it worked once on my machine. On the other hand, there’s probably something useful to be made of it. Pull requests are welcome.

GitX does a decent job to quicky look at the history of a repo. If you’d rather use the CLI, this pretty format is the best I’ve found so far:

```
objc4 $ git log --pretty=format:"%C(bold)%s %C(dim)%ci%Creset%d"
646 2014-10-30 20:55:50 +0000 (HEAD, tag: OS_X-10.10, origin/master, origin/HEAD, master)
551.1 2013-10-29 00:21:36 +0000 (tag: OS_X-10.9.5, tag: OS_X-10.9.4, tag: OS_X-10.9.3, tag: OS_X-10.9.2, tag: OS_X-10.9.1, tag: OS_X-10.9)
532.2 2012-09-28 15:34:15 +0000 (tag: OS_X-10.8.5, tag: OS_X-10.8.4, tag: OS_X-10.8.3, tag: OS_X-10.8.2)
[...]
```


Enjoy, and don’t hesitate to send comments and suggestions via [twitter.com/_nb](http://twitter.com/_nb) or [submit an issue](https://github.com/n-b/tatin/issues).
