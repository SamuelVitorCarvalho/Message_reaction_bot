# WhatsApp Bot - Technical Documentation

This document covers only these two modules:

- Message reaction bot: `bot_reacao.py`
- Poll marking bot: `bot_enquete_v8.py`

## 1. Purpose

Automate message handling on WhatsApp Web using Selenium to:

- React with thumbs-up to messages that match acceptance rules (`bot_reacao.py`).
- Automatically mark poll options when message text matches acceptance rules (`bot_enquete_v8.py`).

Both bots also monitor unread messages from the analyst contact and trigger an alert protocol.

## 2. Functional Scope

### 2.1 Reaction Bot (`bot_reacao.py`)

- Opens WhatsApp Web using persistent profile data in `zap_profile`.
- Opens the group defined in `NOME_DO_GRUPO`.
- Monitors recent messages and extracts text + message ID.
- Applies filters using:
	- `REGRAS_DE_ACEITE` (OR logic across groups)
	- `PALAVRAS_PROIBIDAS` (higher-priority block list)
- If approved, performs UI-based reaction (react icon + thumbs-up emoji).
- Monitors the side panel for unread messages from the analyst.
- When analyst activity is detected:
	- triggers local/remote alerting (ntfy + Alexa + beep)
	- enters pause mode
- When analyst condition is cleared (message read), it executes shutdown protocol.

### 2.2 Poll Bot (`bot_enquete_v8.py`)

- Opens WhatsApp Web using persistent profile data in `zap_profile`.
- Opens the group defined in `NOME_DO_GRUPO`.
- Runs a high-frequency loop to inspect the latest received message.
- Applies `REGRAS_DE_ACEITE` and `PALAVRAS_PROIBIDAS` against message text.
- If approved, searches for `input[type="checkbox"][aria-checked="false"]` inside the message and clicks the first option.
- Monitors unread analyst messages in the side panel.
- On analyst alert, triggers alert protocol and pauses operation.
- Uses a supervisor loop to auto-restart after crashes.

## 3. Technical Architecture

### 3.1 Python Dependencies

- `selenium`
- `webdriver-manager`
- `psutil` (used by poll bot for CPU priority)
- Standard library: `os`, `sys`, `time`, `datetime`, `urllib`, `winsound`

Note: `winsound` is Windows-only.

### 3.2 Platform Requirements

- Windows (`.bat` scripts, `winsound`, `shutdown`, `taskkill`)
- Google Chrome installed
- Internet access for:
	- WhatsApp Web
	- ChromeDriver management (`webdriver-manager`)
	- `ntfy.sh` (if enabled)
	- Voice Monkey (Alexa), if configured

### 3.3 Session Persistence

Both scripts use:

- `NOME_DO_PERFIL = "zap_profile"`

This allows WhatsApp Web login session reuse across runs (avoids repeated QR scan, unless session expires).

### 3.4 External Integrations

- Push notifications via `ntfy.sh` (`TOPICO_NTFY`).
- Alexa announcement via Voice Monkey (`LINK_ALEXA_MONKEY`).
- Local audible alert via `winsound.Beep`.

## 4. Execution Flows

### 4.1 Startup (Common)

1. Terminates Chrome instances (`taskkill`) to reduce session conflicts.
2. Initializes Chrome WebDriver with performance-oriented flags.
3. Opens `https://web.whatsapp.com`.
4. Locates search input and opens configured group.

### 4.2 Processing Flow - Reaction Bot

1. Scrolls to conversation bottom (when available).
2. Checks side panel for unread analyst message.
3. If no alert, processes recent messages and skips previously handled IDs.
4. Evaluates accept/deny rules.
5. On match, reacts with thumbs-up.

### 4.3 Processing Flow - Poll Bot

1. Scrolls to conversation bottom.
2. Checks analyst alert condition.
3. Reads only latest incoming message (`message-in`).
4. If not yet processed, evaluates rules.
5. On match, marks available poll checkbox.

## 5. Business Rules

### 5.1 Rule Model

- Each item in `REGRAS_DE_ACEITE` is a required-term group (AND inside each group).
- The full list is evaluated with OR across groups.
- `PALAVRAS_PROIBIDAS` has precedence over acceptance.

Possible outcomes:

- Approved for automation action.
- Blocked by forbidden term.
- Ignored (no acceptance match).

### 5.2 Analyst Pause Mode

When an unread analyst message is detected:

- Enables `MODO_PAUSA`.
- Triggers alarm once per alert cycle.
- Suspends reaction/vote automation until normalized.
- Under specific conditions, runs machine shutdown routine.

## 6. Configuration

Edit constants at the top of each script:

- `NOME_DO_GRUPO`
- `NOME_DO_ANALISTA`
- `REGRAS_DE_ACEITE`
- `PALAVRAS_PROIBIDAS`
- `TOPICO_NTFY`
- `LINK_ALEXA_MONKEY`
- `NOME_DO_PERFIL`

## 7. Running

### 7.1 Recommended Setup

Create virtual environment at project root:

```bat
python -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install selenium webdriver-manager psutil
```

### 7.2 Start Reaction Bot

```bat
iniciar_bot_reacao.bat
```

Startup file: `iniciar_bot_reacao.bat`

### 7.3 Start Poll Bot

```bat
iniciar_bot_enquete.bat
```

Startup file: `iniciar_bot_enquete.bat`

## 8. Observability and Logs

- Console logs with timestamp (`log(...)`).
- Main events:
	- group open
	- message evaluation/approval/block
	- reaction or vote success/failure
	- analyst alert state
	- automation exceptions

## 9. Resilience

- Poll bot implements `supervisor()` for automatic restart after failures.
- Handles common Selenium exceptions (for example stale/missing elements).
- In general, transient DOM failures are ignored to keep main loop running.

## 10. Technical Limits and Risks

- Strong dependency on WhatsApp Web DOM structure (selector changes may break behavior).
- `taskkill` closes all local Chrome instances (can impact user sessions).
- Automatic machine shutdown is present (`shutdown /s /f /t 30`).
- Tokens/credentials are hardcoded as constants (recommended: move to environment variables).

## 11. Operational Best Practices

- Run bots on a dedicated automation machine.
- Keep WhatsApp session active in `zap_profile`.
- Periodically review XPath/CSS selectors after WhatsApp Web updates.
- Validate accept/deny rules before production use.
- Monitor ntfy/Alexa notifications to confirm alert pipeline health.

## 12. Files Covered by This Document

- `bot_reacao.py`
- `bot_enquete_v8.py`
- `iniciar_bot_reacao.bat`
- `iniciar_bot_enquete.bat`
