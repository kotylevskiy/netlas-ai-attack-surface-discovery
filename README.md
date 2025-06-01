# Netlas AI Attack Surface Discovery

**Netlas AI Attack Surface Discovery** is an experimental automated tool that maps the internet-facing assets of an organization, starting from a single root domain.
It combines the [Netlas](https://netlas.io) Attack Surface Discovery API with OpenAI's GPT models to intelligently expand and evaluate the surface.


## 🚀 How It Works

The algorithm begins with a root domain and builds an **attack surface graph** by recursively discovering related assets via the Netlas API.

For each discovered node (e.g., domain, IP address, mailserver), the tool prompts a GPT model to decide which expansion paths are worth pursuing — such as exploring WHOIS data, DNS records, trackers, or network relationships. The AI can choose to:

* Fully expand a group of results
* Skip irrelevant or noisy groups
* Partially expand and review individual entries

This process repeats for all new assets until either the discovery graph is fully explored or a specified node limit is reached.
The final output is a deduplicated list of discovered assets, grouped by type.


## 📦 Requirements

* Python 3.12+
* A [Netlas API key](https://docs.netlas.io/faq/#api-key) (Business tier or higher required)
* An [OpenAI API key](https://openai.com/api/) for ChatGPT access


## 🛠 Installation

```bash
git clone https://github.com/yourusername/netlas-ai-attack-surface-discovery.git
cd netlas-ai-attack-surface-discovery
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```


## ⚙️ Configuration

Set your API keys either as environment variables or via a `.env` file in the project root:

### Option 1: `.env` file

Create a `.env` file with the following content:

```env
NETLAS_API_KEY=your_netlas_key
OPENAI_API_KEY=your_openai_key
MAX_NODES_TO_PROCESS=50
```

`MAX_NODES_TO_PROCESS` is optional and limits how many nodes are processed in total.


### Option 2: Export variables

```bash
export NETLAS_API_KEY=your_netlas_key
export OPENAI_API_KEY=your_openai_key
```


## 🧪 Usage

```bash
python ai-discovery.py DOMAIN
```

### Positional argument:

* `DOMAIN` – the root domain to begin attack surface discovery from.

### Optional flags:

* `-h`, `--help` — Show help message and exit
* `-v`, `--verbose` — Enable verbose output and debug info
* `-s`, `--silent` — Suppress all output except final results
* `-d`, `--debug` — Output only errors
* `--no-results` — Do not print final results

### Example:

```bash
python ai-discovery.py netlas.io
```


## ⚠️ Disclaimer

This tool was originally built as an experiment to evaluate how well OpenAI models can assist in attack surface discovery — specifically their ability to:

* Distinguish relevant from irrelevant entities
* Filter out noisy or shared infrastructure
* Focus on target-controlled assets

After completing initial development and testing, it became clear that this approach could be useful to the community. That’s why it’s now public.

Feedback, suggestions, and contributions are very welcome!

➡️ Use the [Discussions](https://github.com/yourusername/netlas-ai-attack-surface-discovery/discussions) section or join the [Netlas Community on Discord](https://nt.ls/discord) to connect.

