# Reads PreToolUse JSON from stdin and prints a visible banner when an Agent is spawned.
# Claude Code passes: { "tool_name": "Agent", "tool_input": { "subagent_type": "...", ... } }

$input_json = $Input | Out-String
try {
    $data = $input_json | ConvertFrom-Json
} catch {
    exit 0
}

$agent = $data.tool_input.subagent_type
if (-not $agent) { exit 0 }

# Model map — mirrors AGENT_BOOT.md §2
$model_map = @{
    "prompt-evaluator"      = "Sonnet (claude-sonnet-4-6)"
    "duplicate-detector"    = "Haiku  (claude-haiku-4-5)"
    "artifact-validator"    = "Haiku  (claude-haiku-4-5)"
    "phase-gate"            = "Haiku  (claude-haiku-4-5)"
    "session-finalizer"     = "Haiku  (claude-haiku-4-5)"
    "pyqt-architect"       = "Sonnet (claude-sonnet-4-6)"
    "pyqt-code-writer"     = "Sonnet (claude-sonnet-4-6)"
    "pyqt-code-reviewer"   = "Sonnet (claude-sonnet-4-6)"
    "pyqt-code-simplifier" = "Sonnet (claude-sonnet-4-6)"
    "test-writer"           = "Sonnet (claude-sonnet-4-6)"
    "code-reviewer"         = "Sonnet (claude-sonnet-4-6)"
}

$model = if ($model_map.ContainsKey($agent)) { $model_map[$agent] } else { "Sonnet (default)" }

$message = "AGENT START >> $agent | Model >> $model"
Write-Output (ConvertTo-Json @{ systemMessage = $message } -Compress)
