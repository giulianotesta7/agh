Output assets/agh-workspace-demo.gif

Set Shell "bash"
Set FontSize 26
Set Width 1200
Set Height 660
Set Theme "Dracula"
Set Padding 28
Set WindowBar Colorful
Set TypingSpeed 35ms
Set PlaybackSpeed 0.8

Hide
Type "mkdir -p /tmp/agh-demo/bin /tmp/agh-demo/AgentGuidanceHub && cd /tmp/agh-demo/AgentGuidanceHub" Enter
Type "cat > /tmp/agh-demo/bin/agh <<'EOF'" Enter
Type "#!/usr/bin/env bash" Enter
Type "case $1:$2 in" Enter
Type "  sync:) mkdir -p .agh; echo 'Linked project AgentGuidanceHub'; echo 'Repo: https://github.com/giulianotesta7/AgentGuidanceHub'; echo 'Project file: .agh/project.toml' ;;" Enter
Type "  pull:) if [ ! -f .agh-cache/preferences.toml ]; then echo 'No local agent selected for this workspace.'; echo 'Which agent do you use?'; echo '1. Claude Code'; echo '2. OpenCode'; echo '3. Skip for now'; printf 'Choice [1-3]: '; read choice; echo; if [ $choice = 2 ]; then mkdir -p .agh-cache; echo 'Selected OpenCode for this workspace.'; echo 'Preferences: .agh-cache/preferences.toml'; else echo 'Pull skipped.'; exit 2; fi; echo; fi; echo 'Pull complete: 2 changed, 0 conflicts.'; echo 'Updated:'; echo '  AGENTS.md'; echo '  .opencode/skills/reviewer/SKILL.md'; echo; echo 'Lockfile: .agh/lock.toml' ;;" Enter
Type "esac" Enter
Type "EOF" Enter
Type "chmod +x /tmp/agh-demo/bin/agh && export PATH=/tmp/agh-demo/bin:$PATH" Enter
Type "export PS1=$'\\[\\e[1;36m\\]agh-demo\\[\\e[0m\\] \\[\\e[1;35m\\]❯\\[\\e[0m\\] '" Enter
Type "clear" Enter
Show
Ctrl+L
Sleep 500ms
Type "agh sync" Enter
Sleep 900ms
Type "agh pull" Enter
Sleep 1.2s
Type "2"
Sleep 500ms
Enter
Sleep 2s
