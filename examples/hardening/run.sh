# usage: run.sh dir tag
cd $1; SECONDS=0
echo "Use the ops-agent skill (load it with the Skill tool) to watch production for this service. Look at the last 24 hours of logs and traces, follow the skill, and finish with the final report. No human is available to answer questions." | claude -p --model sonnet --max-turns 20 --output-format json \
 --allowedTools "Read,Write,Edit,Glob,Grep,Skill,Bash(ls*),Bash(cat*),Bash(grep*),Bash(head*),Bash(wc*),Bash(python*),Bash(.venv/bin/python*),Bash(git status*),Bash(git diff*),Bash(git log*),Bash(git checkout*),Bash(git branch*),Bash(git add*),Bash(git commit*)" > ../$2.json 2> ../$2.err
echo $SECONDS > ../$2.secs
