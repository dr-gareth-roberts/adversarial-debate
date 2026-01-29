"""Shell completion scripts for adversarial-debate CLI.

Generates completion scripts for bash, zsh, and fish shells.
"""

BASH_COMPLETION = """
# Bash completion for adversarial-debate
# Add to ~/.bashrc or ~/.bash_completion

_adversarial_debate_completions() {
    local cur prev opts commands agents log_levels exposures formats
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    commands="analyze orchestrate verdict run watch cache"
    agents="exploit break chaos"
    log_levels="DEBUG INFO WARNING ERROR"
    exposures="public authenticated internal"
    formats="json sarif html markdown"
    cache_commands="stats clear cleanup"

    # Global options
    opts="--version --config --log-level --json-output --dry-run --output --help"

    case "${prev}" in
        adversarial-debate)
            COMPREPLY=( $(compgen -W "${commands} ${opts}" -- ${cur}) )
            return 0
            ;;
        analyze)
            COMPREPLY=( $(compgen -W "${agents}" -- ${cur}) )
            return 0
            ;;
        --config|-c)
            COMPREPLY=( $(compgen -f -X "!*.json" -- ${cur}) )
            return 0
            ;;
        --log-level)
            COMPREPLY=( $(compgen -W "${log_levels}" -- ${cur}) )
            return 0
            ;;
        --output|-o)
            COMPREPLY=( $(compgen -d -- ${cur}) )
            return 0
            ;;
        --exposure)
            COMPREPLY=( $(compgen -W "${exposures}" -- ${cur}) )
            return 0
            ;;
        --format)
            COMPREPLY=( $(compgen -W "${formats}" -- ${cur}) )
            return 0
            ;;
        --agent)
            COMPREPLY=( $(compgen -W "${agents} all" -- ${cur}) )
            return 0
            ;;
        cache)
            COMPREPLY=( $(compgen -W "${cache_commands}" -- ${cur}) )
            return 0
            ;;
        exploit|break|chaos)
            # After agent, expect file/directory
            COMPREPLY=( $(compgen -f -- ${cur}) $(compgen -d -- ${cur}) )
            return 0
            ;;
        orchestrate|run|watch)
            # Expect file/directory
            COMPREPLY=( $(compgen -f -- ${cur}) $(compgen -d -- ${cur}) )
            return 0
            ;;
        verdict)
            # Expect JSON file
            COMPREPLY=( $(compgen -f -X "!*.json" -- ${cur}) )
            return 0
            ;;
        *)
            ;;
    esac

    # Default to files and directories
    if [[ ${cur} == -* ]] ; then
        case "${COMP_WORDS[1]}" in
            analyze)
                COMPREPLY=( $(compgen -W "--focus --timeout --help" -- ${cur}) )
                ;;
            orchestrate)
                COMPREPLY=( $(compgen -W "--time-budget --exposure --help" -- ${cur}) )
                ;;
            verdict)
                COMPREPLY=( $(compgen -W "--context --help" -- ${cur}) )
                ;;
            run)
                COMPREPLY=( $(compgen -W "--files --time-budget --parallel \\
--skip-verdict --skip-debate --debate-max-findings --format \\
--report-file --bundle-file --fail-on --min-severity --baseline-file \\
--baseline-mode --baseline-write --help" -- ${cur}) )
                ;;
            watch)
                COMPREPLY=( $(compgen -W "--agent --debounce --patterns --help" -- ${cur}) )
                ;;
            *)
                COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
                ;;
        esac
    else
        COMPREPLY=( $(compgen -f -- ${cur}) $(compgen -d -- ${cur}) )
    fi

    return 0
}

complete -F _adversarial_debate_completions adversarial-debate
"""

ZSH_COMPLETION = """
#compdef adversarial-debate

# Zsh completion for adversarial-debate
# Add to ~/.zshrc or place in fpath directory

_adversarial_debate() {
    local -a commands agents log_levels exposures formats cache_commands

    commands=(
        'analyze:Run a single agent on a target'
        'orchestrate:Create an attack plan'
        'verdict:Run arbiter on findings'
        'run:Run full pipeline'
        'watch:Watch files and re-run analysis on changes'
        'cache:Manage analysis cache'
    )

    agents=(exploit break chaos)
    log_levels=(DEBUG INFO WARNING ERROR)
    exposures=(public authenticated internal)
    formats=(json sarif html markdown)
    cache_commands=(stats clear cleanup)

    _arguments -C \\
        '--version[Show version]' \\
        '(-c --config)'{-c,--config}'[Configuration file]:file:_files -g "*.json"' \\
        '--log-level[Log level]:level:(${log_levels})' \\
        '--json-output[Output as JSON]' \\
        '--dry-run[Preview without executing]' \\
        '(-o --output)'{-o,--output}'[Output path]:path:_files -/' \\
        '--help[Show help]' \\
        '1: :->command' \\
        '*:: :->args'

    case $state in
        command)
            _describe -t commands 'command' commands
            ;;
        args)
            case $words[1] in
                analyze)
                    _arguments \\
                        '1: :->agent' \\
                        '2:target:_files' \\
                        '*--focus[Focus areas]:areas:' \\
                        '--timeout[Timeout seconds]:timeout:' \\
                        '--help[Show help]'
                    case $state in
                        agent)
                            _describe -t agents 'agent' agents
                            ;;
                    esac
                    ;;
                orchestrate)
                    _arguments \\
                        '1:target:_files' \\
                        '--time-budget[Time budget]:seconds:' \\
                        '--exposure[Exposure level]:exposure:(${exposures})' \\
                        '--help[Show help]'
                    ;;
                verdict)
                    _arguments \\
                        '1:findings:_files -g "*.json"' \\
                        '--context[Context file]:file:_files -g "*.json"' \\
                        '--help[Show help]'
                    ;;
                run)
                    _arguments \\
                        '1:target:_files' \\
                        '*--files[Specific files]:file:_files' \\
                        '--time-budget[Time budget]:seconds:' \\
                        '--parallel[Parallel agents]:count:' \\
                        '--skip-verdict[Skip final verdict]' \\
                        '--skip-debate[Skip cross-examination debate]' \\
                        '--debate-max-findings[Max findings for debate]:count:' \\
                        '--format[Report format]:format:(json sarif html markdown)' \\
                        '--report-file[Report path]:path:_files' \\
                        '--bundle-file[Bundle path]:path:_files' \\
                        '--fail-on[Fail on verdict]:mode:(block warn never)' \\
                        '--min-severity[Min severity]:severity:(critical high medium low info)' \\
                        '--baseline-file[Baseline bundle]:path:_files' \\
                        '--baseline-mode[Baseline mode]:mode:(off only-new)' \\
                        '--baseline-write[Write baseline]:path:_files' \\
                        '--help[Show help]'
                    ;;
                watch)
                    _arguments \\
                        '1:target:_files' \\
                        '--agent[Agent to run]:agent:(${agents} all)' \\
                        '--debounce[Debounce delay]:seconds:' \\
                        '*--patterns[File patterns]:pattern:' \\
                        '--help[Show help]'
                    ;;
                cache)
                    _arguments \\
                        '1: :->cache_cmd'
                    case $state in
                        cache_cmd)
                            _describe -t cache_commands 'cache command' cache_commands
                            ;;
                    esac
                    ;;
            esac
            ;;
    esac
}

_adversarial_debate "$@"
"""

FISH_COMPLETION = """
# Fish completion for adversarial-debate
# Save to ~/.config/fish/completions/adversarial-debate.fish

# Disable file completion by default
complete -c adversarial-debate -f

# Commands
complete -c adversarial-debate -n "__fish_use_subcommand" -a "analyze" \\
    -d "Run a single agent on a target"
complete -c adversarial-debate -n "__fish_use_subcommand" -a "orchestrate" \\
    -d "Create an attack plan"
complete -c adversarial-debate -n "__fish_use_subcommand" -a "verdict" -d "Run arbiter on findings"
complete -c adversarial-debate -n "__fish_use_subcommand" -a "run" -d "Run full pipeline"
complete -c adversarial-debate -n "__fish_use_subcommand" -a "watch" \\
    -d "Watch files and re-run on changes"
complete -c adversarial-debate -n "__fish_use_subcommand" -a "cache" -d "Manage analysis cache"

# Global options
complete -c adversarial-debate -l version -d "Show version"
complete -c adversarial-debate -s c -l config -r -d "Configuration file"
complete -c adversarial-debate -l log-level -x -a "DEBUG INFO WARNING ERROR" -d "Log level"
complete -c adversarial-debate -l json-output -d "Output as JSON"
complete -c adversarial-debate -l dry-run -d "Preview without executing"
complete -c adversarial-debate -s o -l output -r -d "Output path"
complete -c adversarial-debate -s h -l help -d "Show help"

# analyze command
complete -c adversarial-debate -n "__fish_seen_subcommand_from analyze" -a "exploit break chaos" \\
    -d "Agent"
complete -c adversarial-debate -n "__fish_seen_subcommand_from analyze" -l focus -d "Focus areas"
complete -c adversarial-debate -n "__fish_seen_subcommand_from analyze" -l timeout -x \\
    -d "Timeout seconds"

# orchestrate command
complete -c adversarial-debate -n "__fish_seen_subcommand_from orchestrate" -l time-budget -x \\
    -d "Time budget seconds"
complete -c adversarial-debate -n "__fish_seen_subcommand_from orchestrate" -l exposure -x \\
    -a "public authenticated internal" \\
    -d "Exposure level"

# verdict command
complete -c adversarial-debate -n "__fish_seen_subcommand_from verdict" -l context -r \\
    -d "Context file"

# run command
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l time-budget -x \\
    -d "Time budget seconds"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l parallel -x \\
    -d "Parallel agents"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l skip-verdict \\
    -d "Skip final verdict"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l files -x \\
    -d "Specific files"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l skip-debate \\
    -d "Skip cross-examination debate"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l debate-max-findings -x \\
    -d "Max findings for debate"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l format -x \\
    -a "json sarif html markdown" \\
    -d "Report format"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l report-file -r \\
    -d "Report path"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l bundle-file -r \\
    -d "Bundle path"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l fail-on -x \\
    -a "block warn never" \\
    -d "Fail on verdict"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l min-severity -x \\
    -a "critical high medium low info" \\
    -d "Min severity"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l baseline-file -r \\
    -d "Baseline bundle"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l baseline-mode -x \\
    -a "off only-new" \\
    -d "Baseline mode"
complete -c adversarial-debate -n "__fish_seen_subcommand_from run" -l baseline-write -r \\
    -d "Write baseline"

# watch command
complete -c adversarial-debate -n "__fish_seen_subcommand_from watch" -l agent -x \\
    -a "exploit break chaos all" \\
    -d "Agent to run"
complete -c adversarial-debate -n "__fish_seen_subcommand_from watch" -l debounce -x \\
    -d "Debounce delay"
complete -c adversarial-debate -n "__fish_seen_subcommand_from watch" -l patterns -d "File patterns"

# cache command
complete -c adversarial-debate -n "__fish_seen_subcommand_from cache" -a "stats clear cleanup" \\
    -d "Cache command"
"""


def get_completion_script(shell: str) -> str:
    """Get completion script for specified shell.

    Args:
        shell: Shell type ('bash', 'zsh', or 'fish')

    Returns:
        Completion script content

    Raises:
        ValueError: If shell is not supported
    """
    scripts = {
        "bash": BASH_COMPLETION,
        "zsh": ZSH_COMPLETION,
        "fish": FISH_COMPLETION,
    }

    if shell not in scripts:
        raise ValueError(f"Unknown shell: {shell}. Supported: bash, zsh, fish")

    return scripts[shell].strip()


def print_completion_script(shell: str) -> None:
    """Print completion script to stdout.

    Args:
        shell: Shell type ('bash', 'zsh', or 'fish')
    """
    print(get_completion_script(shell))


def get_install_instructions(shell: str) -> str:
    """Get installation instructions for shell completions.

    Args:
        shell: Shell type

    Returns:
        Installation instructions
    """
    instructions = {
        "bash": """
# Bash completion installation:

# Option 1: Add to ~/.bashrc
adversarial-debate --completions bash >> ~/.bashrc
source ~/.bashrc

# Option 2: Add to bash-completion directory (if installed)
adversarial-debate --completions bash > /etc/bash_completion.d/adversarial-debate
""",
        "zsh": """
# Zsh completion installation:

# Option 1: Add to ~/.zshrc
adversarial-debate --completions zsh >> ~/.zshrc
source ~/.zshrc

# Option 2: Add to fpath directory
mkdir -p ~/.zsh/completions
adversarial-debate --completions zsh > ~/.zsh/completions/_adversarial-debate
# Then add to ~/.zshrc: fpath=(~/.zsh/completions $fpath)
autoload -Uz compinit && compinit
""",
        "fish": """
# Fish completion installation:

# Add to fish completions directory
mkdir -p ~/.config/fish/completions
adversarial-debate --completions fish > ~/.config/fish/completions/adversarial-debate.fish
""",
    }

    if shell not in instructions:
        return f"Unknown shell: {shell}. Supported: bash, zsh, fish"

    return instructions[shell].strip()
