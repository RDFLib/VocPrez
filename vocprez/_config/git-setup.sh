# 1. Setup BitBucket repo
$ git clone https://nicholascarsurround@bitbucket.org/surroundbitbucket/vocprez.git

# 2. Add Github repo as a new remote in BitBucket called "sync"
$ git remote add sync git@github.com/RDFLib/VocPrez/ -- fix URI

# 3. Verify remotes. Should show "fetch" and "push" for two remotes i.e. "origin" and "sync"
$ git remote -v

# 4. ull from sync's (GitHub's) "master" into local master
$ git pull sync master

# 5. Setup local branch "github" to track "sync" "master"
$ git branch --track github sync/master
# repeatedly pull from local branch github into master to get GitHub updates

# 6. Push local "master" branch, initially from GitHub to Bitbucket
$ git push -u origin master