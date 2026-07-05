# donut-assistant

Simple ReAct agent
Agent generated with `agents-cli` version `0.5.1`

## Project Structure

```
donut-assistant/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   ├── agent_runtime_app.py    # Agent Runtime application logic
│   └── app_utils/             # App utilities and helpers
├── .cloudbuild/               # CI/CD pipeline configurations for Google Cloud Build
├── deployment/                # Infrastructure and deployment scripts
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)
- **Terraform**: For infrastructure deployment - [Install](https://developer.hashicorp.com/terraform/downloads)


## Quick Start

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Agent Runtime                                                                |
| `agents-cli publish gemini-enterprise` | Register deployed agent to Gemini Enterprise                    |
| `agents-cli infra single-project` | Set up single-project infrastructure using Terraform                              |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.

---

## 📖 Donut Shop Virtual Assistant: Beginner's Guide & Walkthrough

Welcome to the **Donut Shop Virtual Assistant** project! This section walks you through the system's core capabilities, how it is structured under the hood, and how you can interact with it step-by-step.

### 1. Project Overview

The Donut Shop Virtual Assistant is an interactive AI-powered application designed to simulate the customer journey at a modern donut boutique. The project brings together two primary layers:
1. **The Backend AI Agent**: Built using Python and the Google Agent Development Kit (ADK) in [app/agent.py](app/agent.py), this agent functions as a smart shopping assistant. It has access to professional "tools" (Python functions) allowing it to retrieve menu details, process cart checkouts, validate discount codes, and credit loyalty points.
2. **The Frontend User Interface**: A premium Web interface in [index.html](../index.html) styled with a modern glassmorphism aesthetic. It renders a 40-item menu grid with taste filters (Chocolaty, Fruity, Classic, and Bold/Adventure) and contains an interactive chat window to simulate real-time conversations with the virtual agent.

Through this project, customers can browse delicious treats, add them to their order, review their cart items, ask the AI for recommendations based on their flavor preferences, apply discount codes, and checkout to earn loyalty points.

### 2. The 40-Item Menu & Discount System

The store offers **40 unique donut types**, categorized into four flavor profiles:
*   **Classic / Glazed**: Traditional glazed rings, old-fashioned cakes, cinnamon rolls, twisted doughs, and nutty glazes.
*   **Chocolaty**: Thick frosting, chocolate cake bases, fudge drizzles, cookies & cream toppings, and s'mores pairings.
*   **Fruity / Sweet**: Infused with real fruit fillings (raspberry jam, lemon curd, key lime custard) or topped with colorful glazes and sprinkles.
*   **Bold / Adventure**: Creative and experimental pastries like bacon-infused maple glazes, croissant-donut hybrids (cronuts), and pretzel-salted caramel toppings.

#### The Coupon System
The store supports multiple discount codes. Some codes are generic, while others target specific items. The system validates codes and applies a **20% discount** to the entire order subtotal if eligible:
*   `FROSTING20`: 20% off frosting products (e.g., Chocolate Frosted Donut).
*   `SPRINKLES30`: 30% off sprinkles products (e.g., Strawberry Sprinkles Donut).
*   `GLAZED10`: 10% off glazed products (e.g., Glazed Donut).
*   `JELLY15`: 15% off jelly products (e.g., Jelly-Filled Donut).
*   `BOSTON25`: 25% off Boston Cream products (e.g., Boston Cream Donut).
*   `MAPLE20`: 20% off maple bacon products (e.g., Maple Bacon Donut).
*   `FRITTER10`: 10% off apple fritters (e.g., Apple Fritter).
*   `BLUEBERRY15`: 15% off blueberry products (e.g., Blueberry Cake Donut).
*   `CHOCO20`: 20% off double chocolate products (e.g., Double Chocolate Donut).
*   `MATCHA25`: 25% off matcha products (e.g., Matcha Green Tea Donut).

### 3. How to Launch and Test the Project

To experience the assistant in your local environment, follow these steps:
1. **Install Dependencies**: Run `agents-cli install` to install required packages.
2. **Start Agent Playground**: Run `agents-cli playground` to start the local AI playground.
3. **Open Frontend**: Open the root [index.html](../index.html) file in a web browser.

### 4. Interactive Scenarios

#### Scenario A: Point-and-Click Ordering
1. On the left panel of the web page, filter the menu by clicking one of the flavor tabs (e.g., **Chocolaty**).
2. Click **Add to Order** on the *S'mores Donut* card.
3. Notice that the chat assistant on the right updates to confirm the addition and displays the current item count.

#### Scenario B: Conversational Chat
You can chat with the virtual assistant:
- Type `"Show me the menu"` to print all 40 options.
- Type `"What do you recommend for a fruity flavor?"` to get fruit-filled suggestions.
- Type `"Add a Maple Bacon Donut and a Boston Cream Donut"` to add them directly.

#### Scenario C: Cart Summaries
- Ask `"What did I order so far?"` or `"my cart"` to see a breakdown of quantities and prices.
- Ask `"How much is my total price?"` to view the grand total.

#### Scenario D: Redeeming Discount Codes
- Type `"Apply code JELLY15"` or click the quick coupon chips to apply active discounts to your cart.

#### Scenario E: The Checkout Pipeline
- Type `"Check out"` or click the checkout button. A checkout pipeline overlay will verify your user registration, validate the discount codes, calculate and credit 100 loyalty points, and log the completed order.

#### Scenario F: Querying Loyalty Points
- Type `"how many loyalty points do I have?"` or `"show my loyalty points"`.
- The assistant will reply with your current points total (e.g. 100 points).

### 5. Backend Tool Specifications

For developers looking at the Python code in [app/agent.py](app/agent.py), the agent operates by matching user messages with the following tools:
1.  **`get_donut_menu()`**: Returns a formatted string detailing the full 40-donut menu and the eligible discount codes.
2.  **`redeem_discount_code(code, user_id)`**: Verifies if a user is registered and checks if the given code is active and has not been redeemed.
3.  **`award_loyalty_points(user_id, order_id, points)`**: Adds points to a user's account. This function is fortified with safety guards (cap guard, transaction guard, double-crediting guard).
4.  **`process_cart_checkout(user_id, cart_id, discount_code)`**: Calculates the cart subtotal, applies the discount (if a valid code is provided), creates a final order log, and automatically awards 100 loyalty points.
5.  **`update_discount_status(admin_id, code, active)`**: Admin tool allowing users in the `ADMIN_USERS` list to toggle whether coupon codes are active or inactive.
6.  **`get_loyalty_points(user_id)`**: Retrieve the total loyalty points balance for a registered user.

### 6. Running Tests

To run the unit and integration tests:
```bash
.venv\Scripts\pytest tests/unit tests/integration
```
To run the agent-level function calling tests:
```bash
.venv\Scripts\pytest tests/test_agent.py
```
