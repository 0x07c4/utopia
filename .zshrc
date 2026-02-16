# Start configuration added by Zim Framework install {{{
#
# User configuration sourced by interactive shells
#

# -----------------
# Zsh configuration
# -----------------

#
# History
#

# Remove older command from the history if a duplicate is to be added.
setopt HIST_IGNORE_ALL_DUPS

#
# Input/output
#

# Set editor default keymap to emacs (`-e`) or vi (`-v`)
bindkey -e

# Prompt for spelling correction of commands.
#setopt CORRECT

# Customize spelling correction prompt.
#SPROMPT='zsh: correct %F{red}%R%f to %F{green}%r%f [nyae]? '

# Remove path separator from WORDCHARS.
WORDCHARS=${WORDCHARS//[\/]}

# -------------------
# zimfw configuration
# -------------------

# Use degit instead of git as the default tool to install and update modules.
#zstyle ':zim:zmodule' use 'degit'

# --------------------
# Module configuration
# --------------------

#
# git
#

# Set a custom prefix for the generated aliases. The default prefix is 'G'.
#zstyle ':zim:git' aliases-prefix 'g'

#
# input
#

# Append `../` to your input for each `.` you type after an initial `..`
#zstyle ':zim:input' double-dot-expand yes

#
# termtitle
#

# Set a custom terminal title format using prompt expansion escape sequences.
# See http://zsh.sourceforge.net/Doc/Release/Prompt-Expansion.html#Simple-Prompt-Escapes
# If none is provided, the default '%n@%m: %~' is used.
#zstyle ':zim:termtitle' format '%1~'

#
# zsh-autosuggestions
#

# Disable automatic widget re-binding on each precmd. This can be set when
# zsh-users/zsh-autosuggestions is the last module in your ~/.zimrc.
ZSH_AUTOSUGGEST_MANUAL_REBIND=1

# Customize the style that the suggestions are shown with.
# See https://github.com/zsh-users/zsh-autosuggestions/blob/master/README.md#suggestion-highlight-style
#ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=242'

#
# zsh-syntax-highlighting
#

# Set what highlighters will be used.
# See https://github.com/zsh-users/zsh-syntax-highlighting/blob/master/docs/highlighters.md
ZSH_HIGHLIGHT_HIGHLIGHTERS=(main brackets)

# Customize the main highlighter styles.
# See https://github.com/zsh-users/zsh-syntax-highlighting/blob/master/docs/highlighters/main.md#how-to-tweak-it
#typeset -A ZSH_HIGHLIGHT_STYLES
#ZSH_HIGHLIGHT_STYLES[comment]='fg=242'

# ------------------
# Initialize modules
# ------------------

ZIM_HOME=${ZDOTDIR:-${HOME}}/.zim
# Download zimfw plugin manager if missing.
if [[ ! -e ${ZIM_HOME}/zimfw.zsh ]]; then
  if (( ${+commands[curl]} )); then
    curl -fsSL --create-dirs -o ${ZIM_HOME}/zimfw.zsh \
        https://github.com/zimfw/zimfw/releases/latest/download/zimfw.zsh
  else
    mkdir -p ${ZIM_HOME} && wget -nv -O ${ZIM_HOME}/zimfw.zsh \
        https://github.com/zimfw/zimfw/releases/latest/download/zimfw.zsh
  fi
fi
# Install missing modules, and update ${ZIM_HOME}/init.zsh if missing or outdated.
if [[ ! ${ZIM_HOME}/init.zsh -nt ${ZIM_CONFIG_FILE:-${ZDOTDIR:-${HOME}}/.zimrc} ]]; then
  source ${ZIM_HOME}/zimfw.zsh init
fi
# Initialize modules.
source ${ZIM_HOME}/init.zsh

# If generated init is stale/broken, rebuild once so required widgets exist.
if (( ! ${+widgets[history-substring-search-up]} )); then
  source ${ZIM_HOME}/zimfw.zsh build >/dev/null 2>&1
  source ${ZIM_HOME}/init.zsh
fi

# ------------------------------
# Post-init module configuration
# ------------------------------

#
# zsh-history-substring-search
#

zmodload -F zsh/terminfo +p:terminfo
# Always provide working Up/Down history navigation.
up_history_widget=up-line-or-history
down_history_widget=down-line-or-history
if (( ${+widgets[history-substring-search-up]} && ${+widgets[history-substring-search-down]} )); then
  up_history_widget=history-substring-search-up
  down_history_widget=history-substring-search-down
fi
# Bind ^[[A/^[[B manually so up/down works both before and after zle-line-init.
for key ('^[[A' '^P' ${terminfo[kcuu1]}) bindkey ${key} ${up_history_widget}
for key ('^[[B' '^N' ${terminfo[kcud1]}) bindkey ${key} ${down_history_widget}
for key ('k') bindkey -M vicmd ${key} ${up_history_widget}
for key ('j') bindkey -M vicmd ${key} ${down_history_widget}
unset up_history_widget down_history_widget
unset key
# }}} End configuration added by Zim Framework install

export PATH="$HOME/.npm-global/bin:$PATH"
export PATH="$HOME/.dotnet:$PATH"

# dep_tools
export PATH=$HOME/workspace/depot_tools:$PATH

# cargo
export PATH=$HOME/.cargo/bin:$PATH

eval "$(zoxide init zsh --cmd cd)"
eval "$(starship init zsh)"

# gdb
export DEBUGINFOD_URLS="https://debuginfod.archlinux.org"

# nvim
alias nvim-lazy='NVIM_APPNAME="nvim-lazyvim" nvim'

export PATH=$HOME/.local/bin:$PATH

alias lsfg='LSFG_PROCESS="miyu"'
alias fa='fastfetch'
alias reboot='systemctl reboot'

# Ensure wrapper function takes precedence over any inherited ls alias.
unalias ls 2>/dev/null
function ls() {
  command eza --icons "$@"
}

function y() {
  local tmp cwd
  tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
  yazi "$@" --cwd-file="$tmp"
  if [[ -f "$tmp" ]]; then
    cwd="$(<"$tmp")"
    if [[ -n "$cwd" && "$cwd" != "$PWD" ]]; then
      builtin cd -- "$cwd"
    fi
  fi
  rm -f -- "$tmp"
}

function 滚() {
  sysup
}

function raw() {
  command ~/.config/scripts/random-anime-wallpaper.sh "$@"
}

# Align completion with wrapper commands.
if (( ${+functions[compdef]} )); then
  (( ${+functions[_eza]} )) && compdef _eza ls
  if (( ${+functions[y]} )); then
    if (( ${+functions[_yazi]} )); then
      compdef _yazi y
    else
      compdef _files y
    fi
  fi
fi

# codex
alias codex-animitta='codex resume 019c3338-cf95-7750-8fd2-539b314545b8'
