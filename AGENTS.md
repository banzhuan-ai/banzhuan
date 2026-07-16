# banzhuan - Agent Guide

Python SDK for the BanZhuan platform APIs (client-side; not deployed to any host). Part of BanZhuan.AI. This directory is an independent git repository; the workspace around it is not a monorepo.

Non-negotiables:

1. Never build or test on Windows: all npm, node, and Python work runs on the EC2 host over SSH.
2. Deploy order is fixed: edit locally, push to GitHub from Windows PowerShell, then pull and operate on EC2.
3. Restart nginx after every rebuild on EC2 to prevent 502 errors.
4. No keyword matching in Builder or AI Chat code paths.
5. No em-dashes; minimal emoji; user-facing pages are bilingual EN and ZH; new pages include Google Analytics id G-V3SHMMXB1F.
6. Fix root causes; never leave unstaged changes locally or on EC2.

Full rules, host inventory, and workspace map: AGENTS.md in the plans repo (../plans/AGENTS.md in a workspace checkout, or github.com/banzhuan-ai/plans). Deploy procedure: not applicable; see the SDK README.
