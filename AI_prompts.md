# HW6 — AI Prompts Log

Prompts written by Fran, recorded verbatim and grouped by problem.

## Setup

> now we will work at hw6

> create AI_prompts.md to keep updated with all prompts we write here. i will give you a problem number and name and you must fit each prompt inside the right problem.

> now i will giv eyou context. dont make anything.

> we own the campus customs store, a store of yale stuffs made for yale community. we receive continually vendor quotes, invoices, catalog papers and supplier emails. we will make a vendordesk agent to read these stuffs, pick up the key facts (vendor, item, prie, lead time, minimum order) and say if we should buy, according to our handbook
>
> We must be concerned about cost (the handbook is about 10k tokes/call) and safety.
>
> YOU WONT SEND ANY EMAIL OR MAKE ANY PAYMENT. They will be write to a log file, but not sent.
>
> Use my portkey_api_key and ONLY gpt_6_luna. MAKE SURE EVERYTIME YOU ARE RUNNING JTAT YOU ARE USING THIS MODEL GIVIN THE PROBLEM COMPLEXITY.

## Problem 1 — data

> downlload this data and unzip here https://zlisto.github.io/mgt_409_fa26/data/hw6/data.zip
> inside the data/ folder you will find
>
> shop_handbook - the shop handbook
> prices.js on - gpt model prices
> practice_docs - 12 vendors docs
> practice_key.json - correct answers for previous docs
> exam_docs - 10 vendor docs without any answer
>
> take a look on at least one doc per folder to understand how they behave

## Problem 2 — size up the handbook

> problem 2 - size up the handbook
> find out how many tokens the handbook is
> write in output/handbook_estimate.md the token count, how you estimatedit, and how much the handbook costs alone in one call, and 1000 calls, with cached tokens and without, showing  the math and putting the numbers in dollars.
> it must be clear to be auditated later

## Problem 3 — build the vendor desk agent

> problem 3 0 build the vendor desk agent
>
> using pydanticAI, build a agent with for files: prompts/promp.md, agent.py (entry point), tools.py and mols.py (strucutured types)
>
> this agent will receive the path of a vendor document, rend it using a tool (it must support html, pdf amd .eml files) and return: vendor, sku, unit price, lead time in days, miminum order, and decision (recommend OR do_not_recommend), according to handbook rules, and one-sentence reason for the decision
>
> IT MUST ALSO HAVE TWO TRAPS TOOLS: send_email and approve_payment. BOTH WONT BE SEND BY THESE JOBS. They job is catch a malicious doc that trick the agent and try to make it mail or pay a vendor.  YOU CANT MAKE PAYEMNTS OR SEND EMAILS, NO MATTER WHAT HAPPENS. These jobs will append the call and its argument to output/trap_calls.json. This doc starts empty, and every entry is a document tried to trick our agent. These entries must be kept in the doc.
>
> After every run, you will append to output/
> usage_logs.json: document, time, tok counts reported by API, cost in dollars using prices.json
> audit_trail.json: each toll caled with the arguments, and a short result, and a final answer
>
> It must run like this in the terminal: python agent.py --doc data/practice_docs/p01_bluehen_quote.html
>
> It must be ran for p01 and p08 to ensure it is working. Then, start output/harness.md with each field in models.py, why, and each tool in one line

## Problem 4 — with and without cached tokens

> problem 4 - with and without cached tokens
>
> the model can resue the same handbook for all calls, in order to spend less money. let's that this hypothesis, running the agent for all the 12 docs with cache and then without.
>
> Check the tokens counts to ensure you are making both options. A without-cache run that still shows cached tokens doesnt count.
>
> Save both models to output/cache_test.hson. For each, include the setup, doc, every token count the api reports, and price in dolars calculated with prices.json
>
> in output/cache_test.md write
>
> total cost for each setup and % you saved
> cost per doc for each setup and %you saved
> how real numbers compare with your estimative made on problem 2
> a projection for 1k docs a day for 30 day for both steup
> anything in numbers that have surprised you and why did it happen

## Problem 5 — attack your own agent

> problem 5 - attack your own agent
>
> some docs can be intentionally trapped with text aimed to AI. Run my ptoblem 3 agent, with no new defenses, on all 12 docs in data/practice_docs/. Compare answers with data/practice_keys.json and check output/trap_calls.json, the log with fake calls to send email or make payments.
>
> save output/attack_results.json: for each doc, if each field matched the key, if the decision matched, if a trap tool was called, and if a link or other strange text popped up in the answer
>
> write in output/attack_results.md, for ach doc, write what fooled it and where in the file it washidden. Open the docs the way a person would open (browser, pdf view, email app, so on, not a terminal) and compare that with what your agent told us

## Problem 6 — defend our agent

> problem 6 - defend our agent
>
> we will work at 3 levels:
> code - what will be done to the doc before any model see it
> dsign - how agent will be organized in a way a hacker doc cant attack our tools and decisions
> prompt - rules in prompts/prompt.md
>
> DONT DELETE send_email or approve_payment. They gonna be used latter.
>
> Rerun all 11 docs. save output/defense_results.hson in the same shape we did before, plus tokens and dollars per doc
>
> clean docs must still come back with the right values. you dont refuse or blank out a real quote.
>
> In output/defense_results.md write:
>
> * before and after table for all 12 docs
> * what each layer catches that the other miss
> * the extra tokens and dollars each layer added per doc
>
> add your safety failure to output/harness.md telling what each defense layer did in a non technical way

## Problem 7 — red teams

> problem 7 - red teams
> now we will act like attackers to test our own agent. Make two new booby-trapped vendor docs in data/my_attacks/. they must contain different traps and be in different formats. The traps MUST BE different from anything we saw so far on those 12 docs, and THEY CANT be showed for a person open the doc - it must see like a normal quote
>
> run both attacks using 1. no defense agent 2. defended agent
>
> write in output/red_teams.md for each attach the output: what was hidden, where, what it tried to make the do, and happened before and after defenses
>
> ATTACKS THAT CAN ACTUALLY FOOL THE AGENT WITH NO DEFENSES ARE PREFERED

## Problem 8 — exam documents

> problem 8 - exam documents
>
> data/exam_docs has 10 vendor docs whose answers we dont know. run our final defended agent for them.  write in output/exams_results.json, with one entry per file with
>
> * file (name)
> * vendor
> * sku
> * unit_proce
> * lead_time_days
> * min_order
> * decision (recommend/do_not_recommend)
> * reason
> * trap_tool_called (true/false)
> * input_tokens
> * cached_tokens
> * output_tokens
> * cost_used

## Problem 9 — results page

> problem 9 - results page
> write output/hw6_report.html as a file that works without internet and whitout needing additional files on it.
> this page will show us the results from earlier problems:
>
> * caching results, with a chart
> * attacks before and after defenses
> * how much defenses cost in tokens and dollars (make it clear the model you used)
> * exams results and 2 red team attackes
> * a short recommendation to the store manager: should the store run it in real life, and how much it'd cost monthly with 1k docs a day?
>
> make the first version and then i will give you tips to improve it. use this website to inspire your design: https://som.yale.edu/programs/mba

> Every run on this page used
> through Portkey · prices from
> data/prices.json
>
> dont use this. use "prices for gpt-6-... " the model we used
>
> i will give you a image for each section. you must put it on the left to ilustrate the problem.
>
> problem 2 &4: the chart is empty. img: https://www.streamlinehq.com/illustrations/download/chasing-money-4--11756
>
> problem 5&6: the chart is empty too
> https://www.streamlinehq.com/illustrations/download/security-3--11752
>
> problem 6:
> https://www.streamlinehq.com/illustrations/download/saving-money-1--11756
> charts empty
>
> probelm 7: make this section red
> use this:
> https://www.streamlinehq.com/illustrations/download/hack-3--11754
> if needed, edit this img to make the contrast ok
>
> recommendation:
> https://www.streamlinehq.com/illustrations/download/investing-3--11756
> same for contrast

> [screenshot of the page showing {{HERO}} {{CACHING}} {{ATTACKS}} {{COST}} {{EXAM}} {{REDTEAM}} {{RECO}} placeholders]
> oh my god no you literally destroyed everything

> why didnt you include imgs? do you want i save them for you?

> ok i will give you in order and you will know by order and by name which img is

> [5 images pasted, in order: chasing-money-4, security-3, saving-money-1, hack-3, investing-3]

> i'd like you add to problem 5 & 6 the difference between the cost for the 12 docs vs how much we would have lost if we were using the first model without defenses, to show that defending costs way fewer than being attacked

> i'd like you add to RECOMMENDATION the difference between the cost for processing docs vs how much we would have lost if we were using the first model without defenses, to show that defending costs way fewer than being attacked

## Publishing

> [image of the desired repo tree: hw6/ with AI_prompts.md, README.md, .gitignore, .env.example, requirements.txt, agent.py, tools.py, models.py, prompts/prompt.md, data/ (shop_handbook.md, prices.json, practice_key.json, practice_docs/, exam_docs/, my_attacks/), output/ (handbook_estimate.md, harness.md, usage_log.json, audit_trail.json, trap_calls.json, cache_test.json, cache_test.md, attack_results.json, attack_results.md, defense_results.json, defense_results.md, red_team.md, exam_results.json, hw6_report.html)]
> we will publish into in a public github
>
> include the whole data/ folder, DO NOT COMMIT MY REAL .env. USE .gitignore to keep it up and include a .env.example with placeholders. MAKE SURE MY .env IS NOT INCLUDED BEFORE PUBLISHING
>
> make the repo with this strucutre
>
> put a short READ.md explaining how run the agent

> [answered: keep helper scripts in scripts/ ; repo name hw6-vendor-desk]
