# Prediction Market Arbitrage Bot

Scroll All the Way Down to View Project Setup (for your own use) ⬇️

Summary/Overview of Project:

In prediction markets, the shares of an event resulting in yes/no will always result in either $0.00 or $1.00. Arbitrage is a transaction that involves no negative cash flow. If buying A costs $0.45 and buying B costs $0.50, the total cost is $0.95 but the payout is guaranteed to be $1.00. This results in a $0.05 profit per share (minus the fees).

By building a bot, it can use Polymarket/Kalshi’s API to scan the platform for any discrepancies (total adds up to < $1.00). The profit will be [ 1 - (P(A) + P(B)) ] * # of shares - Fees. The cost of fees must be accounted for and the final profit must be positive in order for the trade to be successful. The bot must also purchase the shares before the discrepancies close up. 

There are three types of arbitrage that we can tackle:

Buying YES + NO shares on the same platform that is under $1.00.
Buying YES on Polymarket and NO on Kalshi for the same event that is under $1.00.
Combinatorial?

Software Requirements:

Functional Requirements:

We need to get data via Polymarket and Kalshi and format it (parse + standardize) such that it is in a format that we can process.
We need to calculate spreads and net edges (profit after fees) in real time on both platforms.
We need to submit fill orders instantaneously.
We need to continuously monitor prices and automatically sell our positions if the spread corrects itself.

Non-Functional Requirements:

Low latency must be achieved with the bots as trades must be made quickly.
If the bot crashes, we must have a safety sequence to extract our positions.
The bot must manage wallet signatures and private keys locally and securely.
The system must handle API rate limits by decreasing dependencies from different components to ensure smooth operations. 
Have protected API keys and other information.
System uptime 99.99% of the time.

System Architecture:


Main Goal: Make an arbitrage calculator based on Polymarket and Kalshi API that spam calls to arbitrage in the event not the platform (using the new goal).

New Goal: Whenever they add a new bet to predict on, we upload all of the bets to ChatGPT and we will have chatGPT match the markets to make sure that those two markets are arbitrage opportunities. This is to make sure that we are buying from the same event so that we can make money on that arbitrage.

Components (Layered Architecture):

Data Input Layer (websocket .py files): Maintains a connection with Polymarket and Kalshi and constantly updates the local in-memory market information.
Market Matching Layer (market_arbitrage.py): A scheduled task where it obtains information from the data input component (arbitrage opportunities) and sends it to the LLM to verify that the arbitrage opportunity is a result of matching events.
Matching events means that the events are the same (eg. Warriors vs Lakers). Sometimes, arbitrage opportunities emerge from two different events like G-league Warriors vs Lakers but the title does not differentiate them.
Arbitrage Calculation Layer (engine.py): A continuous machine that iterates through the events and checks the data input layer’s data for arbitrage opportunities. It calculates the net profit after fees and also double checks with the market matching layer to verify the arbitrage opportunity is correct.
Bot Execution Layer: Handles buying and selling positions to make money from arbitrage opportunities. Takes information from the arbitrage calculation layer.
Error Prevention Layer: Prevents bot from buying negative spreads.

Github Repository:

https://github.com/syang1290/Prediction-Market-Arbitrage-Bot 

Next Steps after creating initial arbitrage calculator:

Taking in real data instead of using fake data (data input layer)
Build the market matching component
Building the bot to place real trades
Build a simple frontend UI for user interaction

Resources:

Kalshi API Key Document: https://docs.kalshi.com/welcome 
Polymarket API Key Document: https://docs.polymarket.com/api-reference/introduction 
 
Reddit Posts:
https://www.reddit.com/r/PredictionsMarkets/comments/1u1evxv/i_ran_an_arbitrage_bot_on_polymarket_from_jan_to/ 
https://www.reddit.com/r/arbitragebetting/top/?screen_view_count=4&t=all 

Setup Process:

1. Backend Engine Setup
Navigate to the root directory and create a secure virtual environment. This prevents system-wide package conflicts. Run these commands:

python3 -m venv venv
source venv/bin/activate
pip install websockets requests cryptography python-dotenv fastapi uvicorn openai

2. Generating Kalshi Authentication Keys
Kalshi requires an RSA-PSS digital signature for authenticated requests. Generate a 2048-bit or 4096-bit RSA key pair locally. Run these commands:

openssl genrsa -out kalshi_private_key.pem 4096
openssl rsa -pubout -in kalshi_private_key.pem -out kalshi_public_key.pem

- Print your public key (cat kalshi_public_key.pem) and copy the entire output.
- Navigate to Account & Security -> API Keys in your Kalshi dashboard and click Create Key.
- Paste the public key and ensure Read only is selected.
- Copy the generated API Key ID. Note that Kalshi does not store your private key, and you must save it securely immediately.

3. Frontend Setup.
The interface is a React/TypeScript web application utilizing a strict, terminal-style aesthetic. Run these commands:

cd arbitrage-dashboard
npm install

4. Launching the platform.
Run these commands:

uvicorn server:app --reload --port 8000
npm run dev

Finally, you will see a localhost link which will lead you to the dashboard.

