// AI Infrastructure Explorer — the whole dataset.
// This file is hand-maintained. Keep the object below valid JSON (double quotes,
// no trailing commas) so `python3 check.py` can parse and validate it.
// Rules: every number carries a source; a fact without one is a claim, not a fact.
window.DATA =
{
  "meta": {
    "title": "AI Infrastructure Explorer",
    "updated": "2026-09-24",
    "disclaimer": "Research notes, not investment advice. Figures are as reported by the cited source on the stated date."
  },

  "layers": [
    {
      "id": "demand",
      "name": "Labs & hyperscalers",
      "stage": "demand",
      "summary": "The frontier labs and the four big clouds. Their capex is the load the entire chain is being built to carry.",
      "constraint": "Not demand. Every buyer says it is capacity-constrained into 2027. The open question is how the spend is financed once operating cash flow no longer covers it.",
      "watch": "Capex guidance, free cash flow after capex, and any new equity or debt raised to fund it."
    },
    {
      "id": "neoclouds",
      "name": "Neoclouds",
      "stage": "demand",
      "summary": "Companies that buy GPUs in bulk and rent them out: CoreWeave, Nebius, and former bitcoin miners converting powered sites.",
      "constraint": "Capital. Capex runs at several times revenue and is funded by convertibles and equity, so the constraint is access to capital markets, not GPU supply.",
      "watch": "Convertible pricing, capex-to-revenue, contract backlog, and what old GPUs resell for."
    },
    {
      "id": "accelerators",
      "name": "Accelerators & custom silicon",
      "stage": "compute",
      "summary": "The chips everything is designed around: NVIDIA GPUs, AMD Instinct, and the custom XPUs Broadcom and Marvell build for the hyperscalers.",
      "constraint": "Supply, not orders. NVIDIA's own growth guide is a statement of what it can ship. The cost side is now moving: memory content per package is compressing gross margin at both NVIDIA and Broadcom.",
      "watch": "Gross margin direction, the GPU-versus-XPU share, and how much of the customers' spend the chip vendors are financing themselves."
    },
    {
      "id": "systems",
      "name": "Systems & assembly",
      "stage": "compute",
      "summary": "The companies that turn chips into racks and modules: server builders and the contract manufacturers behind the optics brands.",
      "constraint": "Working capital and thin margins. Assemblers warehouse the build at single-digit gross margins; their revenue tracks GPU platform volume, not pricing power.",
      "watch": "Rack shipment cadence by GPU generation and inventory held for customers."
    },
    {
      "id": "networking",
      "name": "Networking & interconnect",
      "stage": "compute",
      "summary": "The switches, retimers and cables that make thousands of GPUs behave as one machine, inside the rack and between racks.",
      "constraint": "Bandwidth per watt. Copper reaches its physical limit at current rack densities, which pushes the industry toward optics and moves the bottleneck one layer down.",
      "watch": "Ethernet versus InfiniBand share, cluster sizes, and the timing of near-packaged and co-packaged optics."
    },
    {
      "id": "optics",
      "name": "Optics & lasers",
      "stage": "supply",
      "summary": "Transceivers, and the lasers inside them. Every optical link needs a laser diode, and the indium phosphide lasers are the scarce part.",
      "constraint": "Laser supply. Broadcom, Lumentum and Sumitomo hold most merchant CW and EML laser capacity, Coherent has withdrawn from merchant supply, and buyers describe lead times as the binding constraint on module output.",
      "watch": "Laser ASPs, capacity announcements with dates attached, and whether module makers can pass cost through."
    },
    {
      "id": "memory",
      "name": "Memory",
      "stage": "supply",
      "summary": "HBM stacked on every accelerator, plus the DRAM and NAND behind it. Three companies make HBM: SK hynix, Samsung and Micron.",
      "constraint": "The tightest layer in the chain in 2026. Contract prices, long-term agreements out to 2030, and gross margins above 80% at Micron and Sandisk. The supply response is dated: new fabs open from early 2027.",
      "watch": "Contract price momentum quarter on quarter, capex guidance, and the opening dates of new capacity."
    },
    {
      "id": "foundry",
      "name": "Foundry & advanced packaging",
      "stage": "supply",
      "summary": "TSMC fabricates every leading accelerator. Advanced packaging (CoWoS and successors) joins the compute die to its HBM, and is the step the OSATs and Intel are trying to add capacity in.",
      "constraint": "Packaging slots. OSATs have warned of a traditional packaging capacity deficit above 20% by 2027; leading-edge wafer capacity is booked and TSMC is raising prices into it.",
      "watch": "TSMC pricing and capex, packaging capacity additions with dates, and whether Intel 18A or Samsung wins a named AI customer."
    },
    {
      "id": "equipment",
      "name": "Fab equipment",
      "stage": "supply",
      "summary": "The tools every wafer passes through. ASML has the only EUV lithography; Applied, Lam and KLA cover deposition, etch and inspection.",
      "constraint": "Not capacity, concentration. A handful of firms, several of them not American, hold near-monopolies on process steps, which makes this layer the pressure point in any export-control move.",
      "watch": "Advanced-packaging tool orders, China revenue share, and export-control changes."
    },
    {
      "id": "materials",
      "name": "Substrates & materials",
      "stage": "supply",
      "summary": "The wafers beneath the chips and lasers: indium phosphide and gallium arsenide substrates, epiwafers, photonics SOI, optical fibre and glass.",
      "constraint": "Indium phosphide. Substrate prices have risen four quarters running, the largest producer makes its wafers in China under export permits, and Bloomberg now calls InP an industry-level risk.",
      "watch": "Substrate and epiwafer price increases, Chinese export permit cadence, and capacity outside China."
    },
    {
      "id": "power",
      "name": "Power & cooling",
      "stage": "supply",
      "summary": "Grid connections, transformers, gas turbines, nuclear contracts, on-site fuel cells, and the liquid cooling that racks above 100kW require.",
      "constraint": "Lead times. Transformers and turbines are quoted in years, not quarters, and only three firms build large gas turbines. Alphabet's own filing says the ceiling on 2027 capacity is shells and power delivery, not chips.",
      "watch": "Equipment lead times, interconnection queue progress, and direct power contracts signed by hyperscalers."
    }
  ],

  "companies": [
    {
      "ticker": "OPENAI", "name": "OpenAI", "layer": "demand", "hq": "US", "listed": false,
      "what": "Frontier model lab and the largest single buyer of compute outside the hyperscalers themselves.",
      "role": "Its training and inference demand is the load the chain is being built for, and increasingly its suppliers are underwriting its ability to pay: NVIDIA has guaranteed the residual value on gigawatts of data-centre leases where OpenAI is the tenant.",
      "bull": "Every operator that serves it says demand exceeds what can be built. If model progress continues, the spend is a floor.",
      "bear": "It does not yet generate the cash to fund its commitments, so the risk it carries is transferred to NVIDIA's balance sheet and to the neoclouds that build for it.",
      "watch": "Whether compute is funded from revenue or from suppliers' balance sheets.",
      "facts": [
        {"text": "NVIDIA signed residual value guaranties on about 4.25GW of Portsmouth data-centre leases with OpenAI as tenant, aggregate payment obligation capped at $105bn, ready-for-service from 2028.", "asOf": "2026-08-17", "source": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/nvda-20260817.htm"},
        {"text": "Combined 2027 training and inference spend for Anthropic and OpenAI reported at $127bn, from internal investor documents.", "asOf": "2026-09-11", "source": "https://x.com/aleabitoreddit/status/2098306366167535766"}
      ]
    },
    {
      "ticker": "ANTHROPIC", "name": "Anthropic", "layer": "demand", "hq": "US", "listed": false,
      "what": "Frontier model lab. Buys compute through Amazon, Google and, increasingly, neoclouds.",
      "role": "The second large source of lab demand, and the one whose deals show frontier demand spilling past the hyperscalers into rented capacity.",
      "bull": "Compute agreements keep growing in size and the lab's own published scenarios assume the buildout continues through 2028.",
      "bear": "Same as OpenAI: the spend is committed ahead of the revenue that would pay for it.",
      "watch": "Size and counterparties of new compute deals.",
      "facts": [
        {"text": "Signed a $35bn AI compute deal with NVIDIA-backed Lambda.", "asOf": "2026-09-01", "source": "https://x.com/aleabitoreddit/status/2094585395224981709"},
        {"text": "Published economic scenarios showing little divergence in outcomes through 2027 and sharp divergence into 2028-2030.", "asOf": "2026-09-09", "source": "https://x.com/aleabitoreddit/status/2097815176838017066"}
      ]
    },
    {
      "ticker": "MSFT", "name": "Microsoft", "layer": "demand", "hq": "US", "listed": true,
      "what": "Azure, the OpenAI partnership, and the Maia custom accelerator programme.",
      "role": "One of the largest GPU buyers and one of three counterparties named on Samsung's long-term memory agreements. Its Maia ramp is a source of demand for custom-silicon suppliers such as Marvell.",
      "bull": "Capex guidance held while demand still exceeds capacity, and management expects to stay free-cash-flow positive through the buildout.",
      "bear": "The AI spend is only as durable as OpenAI's ability to keep paying for Azure capacity.",
      "watch": "Capex guidance and free cash flow after capex; Maia volumes.",
      "facts": [
        {"text": "Quarterly capex $41bn with free cash flow of $19.6bn; full-year guidance around $175bn; expects to remain free-cash-flow positive in 2027.", "asOf": "2026-07-30", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"},
        {"text": "Maia 300 ramp reported at more than 300k units in 2027, expanding to over 1m.", "asOf": "2026-08-16", "source": "https://x.com/aleabitoreddit/status/2091909391238979970"}
      ]
    },
    {
      "ticker": "GOOGL", "name": "Alphabet", "layer": "demand", "hq": "US", "listed": true,
      "what": "Google Cloud, the TPU programme, and the largest in-house accelerator fleet outside NVIDIA's customers.",
      "role": "The clearest test of how the buildout is financed. Its operating business is strong, yet in the first half of 2026 it funded capex from equity and debt rather than operations.",
      "bull": "Cloud grew 82% with margins above 35%, and net property and equipment rose $74.6bn in six months: the capacity is real and it is being sold.",
      "bear": "Free cash flow turned negative, long-term debt doubled in six months, and $49.6bn of equity plus a $40bn at-the-market programme were put in place. Reported net income was mostly unrealised gains on equity stakes.",
      "watch": "A quarter with free cash flow above zero and no new issuance; any draw on the $40bn ATM.",
      "facts": [
        {"text": "Q2 2026 operating cash flow $39.07bn against capital expenditure $44.92bn: free cash flow negative $5.86bn. 2026 capex guidance raised to $195-205bn.", "asOf": "Q2 2026", "source": "https://data.sec.gov/api/xbrl/companyconcept/CIK0001652044/us-gaap/NetCashProvidedByUsedInOperatingActivities.json"},
        {"text": "Raised $49.6bn of equity and mandatory convertible preferred in June, issued $20.3bn of senior notes in the quarter, and signed a $40bn at-the-market programme. Long-term debt went from $46.5bn to $98.2bn in six months.", "asOf": "Q2 2026", "source": "https://s206.q4cdn.com/479360582/files/doc_financials/2026/q2/2026q2-alphabet-earnings-release.pdf"},
        {"text": "Q2 net income $112.1bn, of which $98.0bn was other income, chiefly unrealised gains on equity securities; operating income $40.8bn. Cloud revenue up 82% to $24.8bn.", "asOf": "Q2 2026", "source": "https://s206.q4cdn.com/479360582/files/doc_financials/2026/q2/2026q2-alphabet-earnings-release.pdf"}
      ]
    },
    {
      "ticker": "AMZN", "name": "Amazon", "layer": "demand", "hq": "US", "listed": true,
      "what": "AWS, the Trainium custom accelerator, and a growing portfolio of equity stakes and warrants in its own silicon suppliers.",
      "role": "The largest cloud buyer of accelerators, and the demand-side anchor for custom silicon: it holds warrants or stakes in Qualcomm, Alchip, Marvell, Astera Labs and Applied Optoelectronics.",
      "bull": "Capacity constraints persist into 2027 with most incoming capacity already reserved, and the retail business still supplies the cash that Alphabet has had to raise externally.",
      "bear": "Free cash flow was negative $27bn across the first half and capex guidance keeps rising, partly on higher memory costs. The Alphabet pattern, equity funding capex, is one bad quarter away.",
      "watch": "Any equity or large note issuance to fund capex.",
      "facts": [
        {"text": "Q2 2026 operating cash flow $45.39bn against capex $54.21bn: free cash flow negative $8.82bn, and negative $26.99bn across the first half. 2026 capex guidance about $220bn, raised on higher memory costs.", "asOf": "Q2 2026", "source": "https://data.sec.gov/api/xbrl/companyconcept/CIK0001018724/us-gaap/NetCashProvidedByUsedInOperatingActivities.json"},
        {"text": "Agreement with Qualcomm gives Amazon warrants over roughly a $4bn stake, tied to up to $60bn of milestone revenue from a custom-silicon partnership.", "asOf": "2026-09-08", "source": "https://x.com/aleabitoreddit/status/2097321349555306512"}
      ]
    },
    {
      "ticker": "META", "name": "Meta Platforms", "layer": "demand", "hq": "US", "listed": true,
      "what": "One of the largest AI capex programmes, now also contracting neocloud capacity and selling excess compute.",
      "role": "Direct GPU demand at scale plus the largest customer for several neoclouds, so its capex guidance moves both the accelerator layer and the rental layer.",
      "bull": "Capex range narrowed higher, and management describes compute scarcity as commanding premium offers for capacity.",
      "bear": "No cloud business to sell the capacity into; the return on the spend depends on advertising and on products not yet launched.",
      "watch": "Capex guidance and neocloud contract sizes.",
      "facts": [
        {"text": "Narrowed 2026 capex range higher to $130-145bn; compute scarcity described as commanding premium offers, with industry capacity tight for the foreseeable future.", "asOf": "2026-07-30", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },
    {
      "ticker": "ORCL", "name": "Oracle", "layer": "demand", "hq": "US", "listed": true,
      "what": "Oracle Cloud Infrastructure, a fast-growing AI compute cloud built largely on rented and leased capacity.",
      "role": "Matters for one disclosure above all: it is the first operator to report realised resale prices on old GPU capacity, which is the central number in the GPU-depreciation argument.",
      "bull": "Renewing GPU capacity resold at a 20% premium to the prior contracts on equipment mostly four years and older.",
      "bear": "Oracle's buildout is debt-funded and its customer concentration in a few labs is high.",
      "watch": "Renewal pricing on old capacity, and financing terms.",
      "facts": [
        {"text": "All GPU capacity coming up for renewal was resold at a 20% premium to previous contracts; the majority of the equipment was four years old or older.", "asOf": "2026-09-13", "source": "https://x.com/aleabitoreddit/status/2099048356345696391"}
      ]
    },

    {
      "ticker": "CRWV", "name": "CoreWeave", "layer": "neoclouds", "hq": "US", "listed": true,
      "what": "The largest pure-play GPU cloud, and one of NVIDIA's biggest direct customers.",
      "role": "The reference neocloud: its backlog is the cleanest read on how much frontier demand is spilling past the hyperscalers.",
      "bull": "Backlog above $100bn, and it is still signing contracts for six-year-old A100s, which argues against rapid GPU depreciation.",
      "bear": "The buildout is debt-funded against contracts with a handful of labs; the equity is a bet on those counterparties.",
      "watch": "Backlog growth, debt terms, and customer concentration.",
      "facts": [
        {"text": "Backlog around $104bn plus more than $25bn of new agreements signed in early Q3.", "asOf": "2026-08-11", "source": "https://x.com/aleabitoreddit/status/2091909391238979970"},
        {"text": "Signing contracts for six-year-old A100 GPUs.", "asOf": "2026-08-16", "source": "https://x.com/aleabitoreddit/status/2091909391238979970"}
      ]
    },
    {
      "ticker": "NBIS", "name": "Nebius Group", "layer": "neoclouds", "hq": "NL", "listed": true,
      "what": "European-origin GPU cloud building large NVIDIA clusters, with NVIDIA as an investor.",
      "role": "The example of neocloud economics in full: run-rate revenue of $3bn against capex of $20-25bn, funded by convertibles.",
      "bull": "Palantir named it its preferred sovereign AI infrastructure partner, it was first to deploy NVIDIA's Groq3 LPX, and Oracle's resale disclosure supports the residual value of its fleet.",
      "bear": "First-half capex was 8.3 times revenue, debt exceeds cash after an upsized $5.75bn convertible, and reported profit came from a revaluation gain, not from renting compute. It is a bet on continued capital-market access.",
      "watch": "Conversion premium on the next convertible; sequential run-rate growth.",
      "facts": [
        {"text": "First-half purchases of property, equipment and intangibles $8,130.3m against revenue of $981.3m. Debt $8.55bn against cash of $8.04bn after the August convertible.", "asOf": "H1 2026", "source": "https://www.sec.gov/Archives/edgar/data/0001513845/000110465926094844/nbis-20260812xex99d2.htm"},
        {"text": "First-half net income from continuing operations $430.8m includes a $780.6m equity revaluation gain. Annualised run-rate revenue $3bn at end-June against full-year capex guidance of $20-25bn.", "asOf": "H1 2026", "source": "https://nebius.com/newsroom/nebius-reports-second-quarter-2026-financial-results"},
        {"text": "Palantir named Nebius its preferred sovereign AI infrastructure partner. A designation, not a disclosed contract value.", "asOf": "2026-09-08", "source": "https://x.com/aleabitoreddit/status/2097327653116363127"}
      ]
    },
    {
      "ticker": "IREN", "name": "IREN", "layer": "neoclouds", "hq": "AU", "listed": true,
      "what": "Former bitcoin miner converting its powered sites into GPU hosting.",
      "role": "The template for the miner-to-neocloud pivot: the scarce asset is the grid connection, not the GPUs.",
      "bull": "Owns powered land and interconnects, which is what the buildout is short of; frontier demand for hosted capacity keeps growing.",
      "bear": "Financed by repeated at-the-market equity issuance, which the shareholders pay for.",
      "watch": "Contracted AI hosting revenue versus mining revenue; dilution.",
      "facts": [
        {"text": "Named by the analyst as a company he has criticised before for overusing ATMs and dilution to finance growth.", "asOf": "2026-08-24", "source": "https://x.com/aleabitoreddit/status/2091843192639672553"}
      ]
    },

    {
      "ticker": "NVDA", "name": "NVIDIA", "layer": "accelerators", "hq": "US", "listed": true,
      "what": "Designs the GPUs and the CUDA platform that most AI training and inference runs on.",
      "role": "The centre of the map. Every supplier below sells into its chips; every buyer above is constrained by what it can ship. It is now also a financier of its own demand, through equity stakes, cloud service agreements and lease guarantees.",
      "bull": "Fiscal 2028 growth guided at about 70% on a supply-constrained basis, with management saying unconstrained growth would exceed 100%. The Q3 outlook assumes zero China data-centre revenue, so China is an unpriced option.",
      "bear": "Gross margin guided down for the first time this cycle because memory content per package is rising and NVIDIA is absorbing it. Receivables are $63bn with five customers holding 70%, and total commitments to customers and suppliers reach $366bn. The company is increasingly funding the buyers of its chips.",
      "watch": "Gross margin below 72% would say memory cost is structural; China re-entering the outlook is the upside nobody is carrying.",
      "facts": [
        {"text": "Q2 FY27 revenue $96.2bn, up 106%; data centre $89.0bn, up 117%. Q3 guided to $108bn assuming no data-centre compute revenue from China. Gross margin guided to 74.0% from 75.0% delivered.", "asOf": "2026-08-26", "source": "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000073/q2fy27pr.htm"},
        {"text": "Expects to grow revenue by approximately 70% in fiscal 2028, described as a supply-constrained outlook; projects $1.3T of hyperscaler capex in 2027, up from about $800bn in 2026.", "asOf": "2026-08-26", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"},
        {"text": "Supply commitments of $92bn for the rest of FY27, $87bn in FY28 and $88bn in FY29, against $119bn total a quarter earlier, described as memory and manufacturing capacity. Receivables $63.1bn with five customers holding 70%. Total commitments $366bn including $29bn of cloud service agreements, $25bn of equity investments and $25bn of leases not yet commenced.", "asOf": "Q2 FY27", "source": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm"},
        {"text": "Residual value guaranties on about 4.25GW of data-centre leases, aggregate obligation capped at $105bn, disclosed as an off-balance-sheet obligation with OpenAI as tenant.", "asOf": "2026-08-17", "source": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/nvda-20260817.htm"},
        {"text": "Invested $3.5bn in MediaTek, extending its reach into the custom-ASIC ecosystem.", "asOf": "2026-08-31", "source": "https://x.com/aleabitoreddit/status/2094405648293482965"}
      ]
    },
    {
      "ticker": "AMD", "name": "AMD", "layer": "accelerators", "hq": "US", "listed": true,
      "what": "The main merchant GPU alternative to NVIDIA (Instinct), plus EPYC server CPUs.",
      "role": "The second source. Its Helios rack platform is in production with lab deployments, and its data-centre segment now exceeds half of revenue.",
      "bull": "Data centre more than doubled to 58% of revenue, gross margin expanded 14 points, and the long-term accelerator TAM was raised to $220bn by 2030.",
      "bear": "Buys the same HBM as NVIDIA into a market where memory vendors earn 76-86% margins, without NVIDIA's pricing power or Broadcom's custom-silicon lock-in to absorb the cost. Client and gaming are flat to down.",
      "watch": "A named hyperscaler committing to Instinct at disclosed scale; gross margin through the HBM cost step.",
      "facts": [
        {"text": "Q2 2026 revenue $11.54bn, up 50%; gross margin 53.8% against 39.8% a year earlier. Data centre revenue $6,718m, 58.2% of the company, with segment operating income $2,103m from a $155m loss.", "asOf": "Q2 2026", "source": "https://www.sec.gov/Archives/edgar/data/2488/000000248826000123/amd-20260627.htm"},
        {"text": "Helios in full production with Anthropic and OpenAI deployments; long-term accelerator TAM raised to $220bn by 2030 from $26bn in 2025.", "asOf": "2026-07-29", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },
    {
      "ticker": "AVGO", "name": "Broadcom", "layer": "accelerators", "hq": "US", "listed": true,
      "what": "Custom AI accelerators (XPUs) for Google, Meta and others, plus the Tomahawk and Jericho switch silicon and a large laser business.",
      "role": "The leading custom-silicon alternative to the GPU and the largest AI networking vendor. Also one of the three merchant laser suppliers, which makes its CEO's laser comments a read on the whole optics layer.",
      "bull": "AI revenue guided to roughly $115bn in FY27 and $230bn in FY28, near doubling each year and above what the street modelled; self-funded from $13.7bn of quarterly free cash flow.",
      "bear": "Customer concentration is extreme: one distributor near half of revenue and five end customers at 55%. Gross margin fell as XPUs grew because memory content rides inside the package, so share gains are dilutive by construction.",
      "watch": "Customer concentration falling; December-quarter bookings behind more than one name; gross margin below 72%.",
      "facts": [
        {"text": "Q3 FY26 revenue $29.6bn; AI semiconductor revenue $16.7bn, up 221%, guided to $21.7bn. Free cash flow $13.7bn in the quarter against $59.4bn of total debt. Non-GAAP gross margin 74.9% from 78.4%; the CFO attributed the decline to memory content in XPUs.", "asOf": "2026-09-02", "source": "https://www.sec.gov/Archives/edgar/data/0001730168/000173016826000076/avgo-08022026x8kxex99.htm"},
        {"text": "Guided AI revenue to about $115bn in FY27 and $230bn in FY28, against street models near $180bn; management said demand exceeds the outlook.", "asOf": "2026-09-02", "source": "https://x.com/aleabitoreddit/status/2095261816767283663"},
        {"text": "CEO: demand for lasers, EML or CW, is far surpassing supply across the industry, stated while Broadcom triples its own laser capacity.", "asOf": "2026-09-02", "source": "https://x.com/aleabitoreddit/status/2095279986701951461"}
      ]
    },
    {
      "ticker": "MRVL", "name": "Marvell Technology", "layer": "accelerators", "hq": "US", "listed": true,
      "what": "Custom silicon for hyperscalers, optical DSPs, and interconnect; acquired Celestial AI for photonic fabric.",
      "role": "The second custom-silicon house and the one NVIDIA appears to be cultivating. Its optics executives are also the best public source on the near-packaged and co-packaged optics timeline.",
      "bull": "Google TPU ecosystem agreement with a large warrant, Microsoft's Maia ramp, and NVIDIA's investment in MediaTek pointing at a broader ASIC field that Broadcom no longer owns alone.",
      "bear": "A socket loss at any one hyperscaler is material, and the reported Google deal terms have not been verified in either company's filings.",
      "watch": "Named ASIC wins with volumes; NPO and CPO timing.",
      "facts": [
        {"text": "Google TPU ecosystem agreement reported with a $12.2bn warrant and about $120bn of potential revenue through 2033. Press characterisation: not found in an Alphabet or Marvell filing.", "asOf": "2026-08-19", "source": "https://x.com/aleabitoreddit/status/2091264273007960320"},
        {"text": "SVP of optical engineering at Semicon Taiwan named Europe and Japan as laser sourcing geographies, and put near-packaged optics at late 2027 to 2028 with full co-packaged optics after that.", "asOf": "2026-09-02", "source": "https://x.com/aleabitoreddit/status/2095102771418845551"}
      ]
    },

    {
      "ticker": "SMCI", "name": "Super Micro Computer", "layer": "systems", "hq": "US", "listed": true,
      "what": "Builds GPU-dense servers and full liquid-cooled racks around NVIDIA and AMD accelerators.",
      "role": "One of the largest integrators of GPU platforms into deployable racks; its revenue is a direct read on platform shipment volume.",
      "bull": "FY2027 revenue guided at several times the company's own market value.",
      "bear": "Single-digit margins and a history of accounting and governance problems; the revenue is pass-through GPU value.",
      "watch": "Delivery against the FY2027 guide and margin per rack.",
      "facts": [
        {"text": "FY2027 revenue guided to $65-72bn against a market capitalisation of about $25bn.", "asOf": "2026-08-13", "source": "https://x.com/aleabitoreddit/status/2091909391238979970"}
      ]
    },
    {
      "ticker": "JBL", "name": "Jabil", "layer": "systems", "hq": "US", "listed": true,
      "what": "Contract manufacturer; builds 1.6T optical modules and AI infrastructure hardware.",
      "role": "The manufacturing partner named in Sivers' 1.6T transceiver path, and the lowest-beta way to hold the optical build. It warehouses components for the AI ramp.",
      "bull": "Intelligent Infrastructure revenue up 21%, and 1.6T module orders expected in H1 2027 with the ramp in H2.",
      "bear": "Gross margin 9.5%: optical mix cannot move a blended number at that scale, so the upside is volume, never margin.",
      "watch": "Losing a 1.6T programme; a guide-down in Intelligent Infrastructure.",
      "facts": [
        {"text": "Intelligent Infrastructure revenue $4,169m of $8,751m, up 21.4%, at a 6.1% segment margin. Components held for customers $2.8bn from $1.1bn. Company gross margin 9.5%. Five customers 36% of revenue.", "asOf": "Q3 FY26", "source": "https://www.sec.gov/Archives/edgar/data/898293/000162828026046138/jbl-20260531.htm"},
        {"text": "1.6T LRO transceiver path with Sivers: orders H1 2027, ramp H2 2027, likely multiple hyperscaler customers.", "asOf": "2026-08-30", "source": "https://x.com/aleabitoreddit/status/2093988125144207710"}
      ]
    },
    {
      "ticker": "FN", "name": "Fabrinet", "layer": "systems", "hq": "TH", "listed": true,
      "what": "Contract manufacturer that builds and tests optical transceivers and photonic modules for the branded suppliers.",
      "role": "The assembly floor behind Lumentum, Coherent and others: transceiver volume physically passes through it.",
      "bull": "Volume grows with every optical forecast revision regardless of which brand wins.",
      "bear": "Contract-manufacturing margins; customer concentration in a few optics houses.",
      "watch": "Datacom revenue growth versus the optical module TAM revisions.",
      "facts": []
    },

    {
      "ticker": "ANET", "name": "Arista Networks", "layer": "networking", "hq": "US", "listed": true,
      "what": "Ethernet switching and software for large data-centre and AI back-end networks.",
      "role": "The Ethernet side of the InfiniBand-versus-Ethernet contest for AI cluster fabrics, and the main systems-level competitor to NVIDIA's own networking.",
      "bull": "Hyperscalers building Ethernet-based AI back-ends buy Arista systems on top of Broadcom silicon.",
      "bear": "NVIDIA sells the fabric with the GPU; share depends on hyperscalers choosing open Ethernet over the bundle.",
      "watch": "AI back-end revenue disclosures and Ethernet share of new clusters.",
      "facts": []
    },
    {
      "ticker": "ALAB", "name": "Astera Labs", "layer": "networking", "hq": "US", "listed": true,
      "what": "PCIe and CXL retimers, switches and connectivity chips inside AI servers.",
      "role": "The connectivity between GPUs, CPUs and memory inside the rack; Amazon holds warrants in it.",
      "bull": "Content per rack rises with every generation as signal distances get harder.",
      "bear": "Competes with in-house silicon at the largest customers and with Broadcom and Marvell.",
      "watch": "Design wins per platform generation.",
      "facts": [
        {"text": "Named among the companies in which Amazon holds equity or warrants, alongside Alchip, Marvell and Applied Optoelectronics.", "asOf": "2026-09-08", "source": "https://x.com/aleabitoreddit/status/2097321349555306512"}
      ]
    },
    {
      "ticker": "CRDO", "name": "Credo Technology", "layer": "networking", "hq": "US", "listed": true,
      "what": "Active electrical cables, SerDes and optical DSPs for data-centre interconnect.",
      "role": "Sits at the copper-to-optical boundary and benefits whichever side of the 800G and 1.6T transition wins.",
      "bull": "Copper in the rack lasts longer than the optics bulls expect, and AECs are the cheap way to stretch it.",
      "bear": "If optics moves into the package on schedule, the copper runway shortens.",
      "watch": "AEC volumes and the NPO and CPO timeline.",
      "facts": []
    },

    {
      "ticker": "LITE", "name": "Lumentum", "layer": "optics", "hq": "US", "listed": true,
      "what": "Lasers and optical components inside data-centre transceivers, and one of the three large merchant laser suppliers.",
      "role": "The laser supplier that is visibly clearing the constraint: record EML shipments, initial 1.6T production, and gross margin expansion that reads as pricing power.",
      "bull": "FY26 revenue up 83%, gross margin from 28% to 42%, and the next quarter guided to the company's own target model early.",
      "bear": "The convertible equitisation created a permanent 28% increase in share count and a $7.8bn extinguishment loss; 79% of revenue ships outside the US into tariff and export-control risk; the price assumes the shortage outlasts the capacity response.",
      "watch": "The conversion requests clearing with a settled share count; non-GAAP operating margin below 35%.",
      "facts": [
        {"text": "FY26 net revenue $3,014.0m, up 83.2%; gross margin expanded from 28.0% to 41.7%. Q1 FY27 guided to $1.225-1.275bn at 39.5-40.5% non-GAAP operating margin. Record 100G/200G EML shipments and initial 1.6T module production.", "asOf": "2026-08-12", "source": "https://investor.lumentum.com/financial-news-releases/news-details/2026/Lumentum-Announces-Fourth-Quarter-and-Full-Fiscal-Year-2026-Results/default.aspx"},
        {"text": "Fiscal 2026 carried a $7,756.6m loss on debt extinguishment from convertible equitisation; shares outstanding rose from 69.9m to 89.7m. 79.2% of revenue outside the United States, 58.2% into Asia-Pacific.", "asOf": "FY2026", "source": "https://www.sec.gov/Archives/edgar/data/1633978/000162828026057358/lite-20260627.htm"}
      ]
    },
    {
      "ticker": "COHR", "name": "Coherent", "layer": "optics", "hq": "US", "listed": true,
      "what": "One of the few suppliers able to ship 800G and 1.6T transceivers at volume, with its own laser fabs.",
      "role": "Structurally important for what it stopped doing: it has withdrawn from merchant indium phosphide laser supply and expects to buy in some datacom lasers. That tightens supply for everyone else and turns Coherent into a buyer of the scarce input.",
      "bull": "Fiscal 2027 essentially booked, long-term agreements running to the end of the decade, and a far cheaper multiple than Lumentum for the same demand.",
      "bear": "Weaker margins than Lumentum, a 790bp gap between GAAP and non-GAAP operating margin, and a cost line now exposed to bought-in laser prices.",
      "watch": "Gross margin attributed to bought-in laser cost; any return to merchant supply.",
      "facts": [
        {"text": "FY2026 revenue $7.12bn; non-GAAP gross margin 39.4% and operating margin 20.5% (GAAP operating margin 12.6%). Q4 revenue $2.046bn, up 33.8%.", "asOf": "FY2026", "source": "https://www.sec.gov/Archives/edgar/data/820318/000119312526346860/d128030dex991.htm"},
        {"text": "Management said it does not see selling indium phosphide lasers externally in the near future and that over the long term some portion of datacom lasers will be bought in.", "asOf": "2026-09-16", "source": "https://x.com/aleabitoreddit/status/2100290486569505223"}
      ]
    },
    {
      "ticker": "AAOI", "name": "Applied Optoelectronics", "layer": "optics", "hq": "US", "listed": true,
      "what": "Optical transceiver maker with its own laser diode production, expanding in the US and Taiwan.",
      "role": "The clearest case of demand outrunning a small company's balance sheet: revenue nearly doubling, guided up again, and funded by repeated equity issuance.",
      "bull": "Q3 guided 33-51% above Q2 on 1.6T volume, capacity build filed and funded, and Amazon holds warrants.",
      "bear": "Three customers are 92% of revenue and a cable-TV distributor holds two thirds of receivables, which stand at 164% of quarterly revenue. Three equity raises since April, roughly $1.7bn, with operating cash flow negative.",
      "watch": "Receivables falling as a share of sales with 1.6T revenue recognised; a Digicomm provision or days sales outstanding above 180.",
      "facts": [
        {"text": "Q2 revenue $191.9m; Q3 guided to $255-290m. Top three customers 42%, 26% and 24% of revenue. Digicomm held $211.0m of $314.0m in receivables. Half-year net loss $37.1m; net ATM proceeds $1.03bn in the half; weighted shares from 56.8m to 81.6m.", "asOf": "Q2 2026", "source": "https://www.sec.gov/Archives/edgar/data/0001158114/000143774926026278/aaoi20260630_10q.htm"},
        {"text": "New $600m at-the-market programme at a $129.10 reference price, the third raise since April; proceeds committed only to general corporate purposes.", "asOf": "2026-08-24", "source": "https://www.sec.gov/Archives/edgar/data/1158114/000110465926099685/tm2623389-1_424b5.htm"}
      ]
    },
    {
      "ticker": "MTSI", "name": "MACOM", "layer": "optics", "hq": "US", "listed": true,
      "what": "Lasers, drivers and TIAs inside transceivers, at roughly double the gross margin of the module assemblers.",
      "role": "The analog and photonic content beneath the transceiver, and a data point on how late merchant CW laser capacity actually arrives: its 75mW part is still in reliability testing with production a potential late-2027 start.",
      "bull": "Revenue accelerating 21-24% sequentially into the guide at 58% gross margin, with operating leverage arriving now.",
      "bear": "China is 39% of revenue and rising; the CW laser programme is later, softer and lower-power than Lumentum ships.",
      "watch": "Fiscal Q4 at or above $425m with data-centre growth intact; a dated first-generation CPO win.",
      "facts": [
        {"text": "Q3 FY26 revenue $342.2m, up 35.8% year on year and 18.4% sequentially, at 58.3% gross margin; Q4 guided to $415-425m. China $133.8m of revenue, 39%.", "asOf": "2026-08-13", "source": "https://www.sec.gov/Archives/edgar/data/0001493594/000149359426000036/ex99_1earningsreleaseq3fy26.htm"},
        {"text": "The CW laser is a 75mW part still in HTOL reliability testing; production a potential start in late calendar 2027, with near-packaged optics revenue expected from 2028.", "asOf": "2026-08-13", "source": "https://www.fool.com/earnings/call-transcripts/2026/08/13/macom-mtsi-q3-2026-earnings-call-transcript/"}
      ]
    },
    {
      "ticker": "SIVE", "name": "Sivers Semiconductors", "layer": "optics", "hq": "SE", "listed": true,
      "what": "Small Swedish maker of indium phosphide CW DFB lasers for pluggables and co-packaged optics.",
      "role": "The merchant laser entrant: reference laser in GlobalFoundries' silicon-photonics platform, a 1.6T path with Jabil, and a dated capacity plan to more than 100m lasers a year. Also the example of a capacity story priced before the orders exist.",
      "bull": "Six new pluggable engagements, a $1.2bn opportunity pipeline, price increases confirmed by channel checks, and a company-stated capacity date.",
      "bear": "Revenue is contracting while the pipeline grows; the Glasgow release states no customer commitments; institutions that bought the July placement at SEK 57 were down by half within ten weeks.",
      "watch": "A named customer commitment against the Glasgow capacity; a further raise below SEK 57 or the Q4 2027 date slipping.",
      "facts": [
        {"text": "Q2 2026 net sales SEK 53.8m, down 12%; adjusted EBITDA SEK -35.5m. Revenue opportunity pipeline about $1.2bn, up 268% since December; six new pluggable engagements.", "asOf": "2026-08-27", "source": "https://www.sivers-semiconductors.com/press/sivers-semiconductors-reports-q2-2026-results-as-product-growth-record-pipeline-and-customer-ramps-position-company-for-growth-acceleration/"},
        {"text": "Placed 12,280,701 shares at SEK 57 in a directed issue of about SEK 700m, oversubscribed.", "asOf": "2026-07-01", "source": "https://www.sivers-semiconductors.com/press/sivers-semiconductors-has-resolved-on-a-directed-share-issue-of-shares-amounting-to-approximately-sek-700-million/"},
        {"text": "USD 30m investment in Glasgow for capacity above 100 million CW DFB lasers annually, operational Q4 2027. The release states no customer commitments.", "asOf": "2026-09-03", "source": "https://www.sivers-semiconductors.com/press/sivers-semiconductors-invests-usd-30-million-to-expand-european-photonics-manufacturing-for-ai-datacenters/"},
        {"text": "Global CW and EML laser capacity cited at roughly 608.4m units a year (TrendForce, July), with Broadcom, Lumentum and Sumitomo making up about 335m.", "asOf": "2026-09-03", "source": "https://x.com/aleabitoreddit/status/2095546138510459218"}
      ]
    },

    {
      "ticker": "MU", "name": "Micron Technology", "layer": "memory", "hq": "US", "listed": true,
      "what": "US maker of DRAM, NAND and HBM; one of three HBM suppliers.",
      "role": "The purest listed expression of the memory squeeze, and the one whose margin shows what the squeeze is made of: nearly all incremental revenue is price.",
      "bull": "Revenue up 346% at 85% gross margin, HBM4 for Vera Rubin shipping since March and ramping twice as fast as HBM3E.",
      "bear": "At 85% gross margin the earnings base is a spot-price artefact; a single-digit ASP decline removes a disproportionate share of profit, and SK hynix's new capacity opens in early 2027.",
      "watch": "Gross margin guided below 75%, or 2027 HBM pricing contracted lower; the 30 September results against the company's own $50bn revenue and $31 EPS bar.",
      "facts": [
        {"text": "Fiscal Q3 2026 revenue $41.5bn, up 346%; gross margin 84.9% with Q4 guided near 86%. HBM4 for Vera Rubin shipping since March 2026, ramping at roughly twice the pace of HBM3E 12-high.", "asOf": "FQ3 2026", "source": "https://investors.micron.com/static-files/631b1a32-5537-46ae-8f40-82e42fc79dfe"},
        {"text": "Fiscal Q4 results due 30 September 2026; the company's own guidance is $50bn revenue and $31 EPS.", "asOf": "2026-09-15", "source": "https://investors.micron.com/news/press-release/2026/Micron-Technology-to-Report-Fiscal-Fourth-Quarter-Results-on-September-30-2026/default.aspx"},
        {"text": "Quarterly gross margin ran 56.0%, 74.4% and 84.6% across the three quarters to 28 May 2026. No memory cycle has held a peak near this.", "asOf": "2026-08-25", "source": "https://data.sec.gov/api/xbrl/companyconcept/CIK0000723125/us-gaap/GrossProfit.json"}
      ]
    },
    {
      "ticker": "000660.KS", "name": "SK hynix", "layer": "memory", "hq": "KR", "listed": true,
      "what": "The leading HBM supplier and NVIDIA's most critical memory partner.",
      "role": "The least fragile way to own the squeeze: a 76% operating margin and a large net cash position. Also the company whose capacity plan dates the end of the squeeze.",
      "bull": "HBM4 in mass shipment, long-term agreements with about ten customers, and management saying the shortage lasts to the end of 2030.",
      "bear": "Capital discipline is the wording; accelerating M15X and a Yongin fab opening in early 2027 is the substance. A third of headline profit sits below the operating line.",
      "watch": "Yongin pulled forward again or 2027 capex above 2026; capex flat with contract prices rising.",
      "facts": [
        {"text": "Q2 2026 revenue 79.3tn won with operating profit 60.5tn won, a 76% margin; net profit 93.9tn won; net cash 69.4tn won. HBM4 in mass shipment; long-term agreements with about ten major customers; M15X accelerating and Yongin Phase 1 cleanroom opening early 2027.", "asOf": "Q2 2026", "source": "https://news.skhynix.com/en/q2-2026-business-results/"},
        {"text": "CEO expects the memory shortage to last until the end of 2030.", "asOf": "2026-08-28", "source": "https://x.com/aleabitoreddit/status/2093252439973777674"},
        {"text": "Samsung and SK hynix stockpiles reported below ten days of supply; KB Securities forecasts the tightest supply conditions in history next year.", "asOf": "2026-09-07", "source": "https://x.com/aleabitoreddit/status/2096858276290015563"}
      ]
    },
    {
      "ticker": "005930.KS", "name": "Samsung Electronics", "layer": "memory", "hq": "KR", "listed": true,
      "what": "The largest memory maker and the third HBM supplier, plus its own foundry and the Samsung Electro-Mechanics substrate business.",
      "role": "The swing supplier in HBM qualification and the counterparty on the longest memory agreements reported anywhere: capacity reserved to 2031.",
      "bull": "Reportedly reserved about 70% of memory capacity through 2031 under long-term agreements with NVIDIA, Microsoft and Google, which is five years of demand visibility.",
      "bear": "HBM share has lagged SK hynix on qualification; the glass-substrate programme at Samsung Electro-Mechanics has slipped to 2028.",
      "watch": "HBM4 qualification at NVIDIA and the terms of the reported long-term agreements.",
      "facts": [
        {"text": "Reported to have reserved about 70% of memory production capacity through 2031 via long-term agreements, with NVIDIA, Microsoft and Google as main counterparties.", "asOf": "2026-08-31", "source": "https://x.com/aleabitoreddit/status/2094365307876040857"}
      ]
    },
    {
      "ticker": "SNDK", "name": "Sandisk", "layer": "memory", "hq": "US", "listed": true,
      "what": "NAND flash maker spun out of Western Digital.",
      "role": "The NAND half of the squeeze, and the company that states most plainly what the growth is: two thirds price, one third volume.",
      "bull": "Data-centre revenue up 103% sequentially, gross margin 84.6%, $93bn of minimum contracted revenue, and management expecting 80% margins to hold to 2030.",
      "bear": "A 71.5% annual gross margin in NAND is a cycle peak, not a run rate; consumer revenue fell 32% sequentially; the board authorised a $14bn buyback at peak-cycle prices with peak-cycle cash.",
      "watch": "Gross margin guided below 70%; contract price momentum slowing.",
      "facts": [
        {"text": "FY2026 revenue $20,248m against $7,355m a year earlier; gross margin 71.5% against 30.1% and 16.1% in the two prior years. Top ten customers 44% of revenue, none above 10%.", "asOf": "FY2026", "source": "https://www.sec.gov/Archives/edgar/data/2023554/000162828026057406/sndk-20260703.htm"},
        {"text": "Q4 data-centre revenue $2,977m, up 103% sequentially from $213m a year earlier. Gross margin 84.6%. Sequential growth about one third volume and two thirds price; consumer revenue down 32% sequentially.", "asOf": "2026-08-05", "source": "https://www.sec.gov/Archives/edgar/data/2023554/000162828026053346/sndkq4-26ex991xpressrelease.htm"},
        {"text": "Board authorised an additional $14bn buyback, funded from operating cash flow. Minimum contracted revenue $93bn.", "asOf": "2026-08-05", "source": "https://www.sec.gov/Archives/edgar/data/2023554/000162828026053346/sndk-20260805.htm"},
        {"text": "TrendForce: 3Q26 NAND contract prices up 10-15% quarter on quarter, a slower pace than prior quarters on weaker consumer demand and a higher base.", "asOf": "2026-07-03", "source": "https://www.trendforce.com/presscenter/news/20260703-13134.html"}
      ]
    },
    {
      "ticker": "CXMT", "name": "ChangXin Memory", "layer": "memory", "hq": "CN", "listed": true,
      "what": "China's largest DRAM maker, listed in July 2026; commodity DDR with domestic HBM ramping.",
      "role": "The standing bear case against the memory trade: capacity added here is what would relieve the allocation squeeze the Korean and US makers' pricing depends on.",
      "bull": "Domestic demand and state support give it a protected market to scale in.",
      "bear": "Listed at a valuation that priced years of growth on day one.",
      "watch": "HBM qualification with Chinese accelerator makers; DRAM output growth.",
      "facts": [
        {"text": "IPO day-one move of about 470%, to roughly $487bn from $85.5bn.", "asOf": "2026-07-29", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },

    {
      "ticker": "TSM", "name": "TSMC", "layer": "foundry", "hq": "TW", "listed": true,
      "what": "The dominant contract foundry; fabricates every NVIDIA GPU and most other leading accelerators, and runs the CoWoS packaging every one of them needs.",
      "role": "The one node everything passes through. It has demonstrated it can raise prices straight into margin, and its COUPE platform is where silicon photonics gets integrated into the package.",
      "bull": "Pricing power at the centre of the buildout; Taiwanese names recovered faster than US and European ones through the September drawdown.",
      "bear": "Geopolitics, and an upstream chokepoint of its own in Japanese and Chinese materials such as tungsten hexafluoride.",
      "watch": "Intel 18A or Samsung winning a named AI customer; a capex cut, which would say TSMC doubts the 2027 demand its customers guide to.",
      "facts": [
        {"text": "VP of Advanced Packaging: foundries can scale the optical engine, but the real bottlenecks to large-scale deployment are lasers, optical fibre, fibre-optic connectors and test.", "asOf": "2026-08-31", "source": "https://x.com/aleabitoreddit/status/2094298008955535500"},
        {"text": "Price increases of about 10% cited at a market value near $1.9T.", "asOf": "2026-06-27", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },
    {
      "ticker": "INTC", "name": "Intel", "layer": "foundry", "hq": "US", "listed": true,
      "what": "x86 CPUs plus Intel Foundry, the US-based alternative to TSMC at the leading edge and in advanced packaging.",
      "role": "The only credible second source for leading-edge wafers and packaging on US soil. Its CPU business is also a beneficiary of the shortage: server CPU prices are rising.",
      "bull": "Signing CPU long-term agreements with Chinese AI data-centre customers at rising prices, and raising PC CPU prices 10%.",
      "bear": "Foundry has no named leading-edge AI customer yet; the turnaround consumes cash.",
      "watch": "A named 18A external AI customer.",
      "facts": [
        {"text": "Reported to be raising PC CPU prices by 10% in October (Digitimes).", "asOf": "2026-09-08", "source": "https://x.com/aleabitoreddit/status/2097232588796780856"},
        {"text": "Signing CPU long-term agreements with Chinese AI data-centre customers amid CPU prices up more than 40% year to date in China.", "asOf": "2026-07-26", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },
    {
      "ticker": "GFS", "name": "GlobalFoundries", "layer": "foundry", "hq": "US", "listed": true,
      "what": "Specialty foundry (not leading-edge) with a silicon-photonics platform that uses Sivers lasers as its reference light source.",
      "role": "The photonics foundry partner for co-packaged optics outside TSMC, with the US government as a shareholder. A 2028 option attached to a mature-node business.",
      "bull": "US government stake, and a silicon-photonics platform that Ayar Labs and others build on.",
      "bear": "The option is a year further out than it looked in August, and mature-node utilisation carries the valuation meanwhile.",
      "watch": "A disclosed silicon-photonics production win with volumes.",
      "facts": [
        {"text": "US government took a material stake; CPO expected to re-accelerate revenue.", "asOf": "2026-08-17", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },
    {
      "ticker": "AMKR", "name": "Amkor Technology", "layer": "foundry", "hq": "US", "listed": true,
      "what": "The largest US-headquartered outsourced assembly and test provider, building advanced packaging capacity in Arizona.",
      "role": "The packaging capacity NVIDIA is prepaying for, and the US answer to the OSAT capacity deficit.",
      "bull": "NVIDIA prepayments of $1.5bn for US capacity and a ten-year TSMC packaging partnership backstop the growth.",
      "bear": "OSAT margins; the capacity arrives in 2027-2028, not now.",
      "watch": "Arizona line timing and utilisation.",
      "facts": [
        {"text": "OSAT providers have warned clients that traditional packaging capacity could face a deficit exceeding 20% by 2027.", "asOf": "2026-08-29", "source": "https://x.com/aleabitoreddit/status/2093712497949950242"},
        {"text": "NVIDIA committed $1.5bn in prepayments for US capacity including Arizona; ten-year TSMC packaging partnership.", "asOf": "2026-08-03", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },
    {
      "ticker": "ASX", "name": "ASE Technology", "layer": "foundry", "hq": "TW", "listed": true,
      "what": "The world's largest outsourced semiconductor assembly and test provider.",
      "role": "The packaging step most chips that are not on CoWoS pass through, and the largest beneficiary of the warned OSAT capacity deficit.",
      "bull": "Packaging is the binding constraint on accelerator supply and ASE has the most of it.",
      "bear": "Capital-intensive, and the highest-value packaging stays inside TSMC.",
      "watch": "Advanced packaging capacity additions and pricing.",
      "facts": []
    },

    {
      "ticker": "ASML", "name": "ASML", "layer": "equipment", "hq": "NL", "listed": true,
      "what": "Sole supplier of EUV lithography, with Zeiss and Trumpf beneath it.",
      "role": "The industry's singular chokepoint: no leading-edge node exists without its tools. Also the clearest example that the real monopolies in the chain are European and Japanese, not American.",
      "bull": "Every leading-edge capacity addition anywhere buys its machines.",
      "bear": "China revenue exposure to export controls; orders are lumpy.",
      "watch": "High-NA adoption and export-control changes.",
      "facts": [
        {"text": "Mapped as a European monopoly in EUV alongside Zeiss SMT and Trumpf; a Japanese cluster holds 90-100% share in EUV photoresist, coat and develop, mask inspection and blanks.", "asOf": "2026-09-04", "source": "https://x.com/aleabitoreddit/status/2095823005595439615"}
      ]
    },
    {
      "ticker": "AMAT", "name": "Applied Materials", "layer": "equipment", "hq": "US", "listed": true,
      "what": "The largest supplier of deposition, etch and inspection tools, and a growing advanced-packaging tool business.",
      "role": "The equipment read on the packaging constraint: its advanced-packaging growth guide and customer discussions out to 2030.",
      "bull": "Advanced packaging growth guidance raised above 70% for 2026, with customer discussions extending to 2030.",
      "bear": "China share of revenue and export-control exposure.",
      "watch": "Advanced-packaging orders with delivery years.",
      "facts": [
        {"text": "Raised 2026 advanced packaging growth guidance to more than 70% from more than 50%; customer discussions now extend to 2030.", "asOf": "2026-08-16", "source": "https://x.com/aleabitoreddit/status/2091909391238979970"}
      ]
    },
    {
      "ticker": "LRCX", "name": "Lam Research", "layer": "equipment", "hq": "US", "listed": true,
      "what": "Etch and deposition equipment for leading-edge logic and memory.",
      "role": "The tool vendor most exposed to memory capex: HBM stacks and 3D NAND are etch-intensive.",
      "bull": "Memory makers' 2027 capacity additions are its orders.",
      "bear": "If memory capex is disciplined, as SK hynix claims, the order cycle is muted.",
      "watch": "Memory equipment orders against the makers' capex guides.",
      "facts": []
    },
    {
      "ticker": "KLAC", "name": "KLA", "layer": "equipment", "hq": "US", "listed": true,
      "what": "Process control and inspection equipment.",
      "role": "Yield control at the advanced nodes and packaging steps AI chips depend on; inspection intensity rises with each node.",
      "bull": "Highest margins in equipment; content grows with process complexity.",
      "bear": "Same China and cycle exposure as the rest of the layer.",
      "watch": "Advanced packaging inspection orders.",
      "facts": []
    },

    {
      "ticker": "AXTI", "name": "AXT", "layer": "materials", "hq": "US", "listed": true,
      "what": "Indium phosphide and gallium arsenide substrates, the base wafers under lasers and RF chips, made by its Beijing Tongmei subsidiary.",
      "role": "The substrate chokepoint under the entire optics layer, and the example of jurisdiction risk: the scarce asset sits inside China and needs export permits to leave.",
      "bull": "Four consecutive substrate price increases, gross margin from 8% to 45%, and Bloomberg now describing InP substrates as an industry-level risk.",
      "bear": "China is 66% of revenue, exports need Chinese permits the company lists as a live uncertainty, and the $550m raised in April to expand capacity is deployed inside that jurisdiction. The shares trade below the placement price.",
      "watch": "Permits granted on a routine cadence with China falling as a share of revenue; a refusal or a Tongmei redemption event.",
      "facts": [
        {"text": "Q2 2026 revenue $47.6m, up 164.8%; gross margin 44.9% from 8.0%; net income $11.1m. China 66% of revenue; indium phosphide exports require Chinese export permits listed as an uncertainty; Chinese private-equity holders retain redemption rights over Tongmei.", "asOf": "Q2 2026", "source": "https://www.sec.gov/Archives/edgar/data/1051627/000143774926027677/axti20260630_10q.htm"},
        {"text": "Sold 8,560,311 shares at $64.25 in April for about $550m to expand Tongmei's indium phosphide capacity; cash and investments $715.8m.", "asOf": "2026-04-30", "source": "https://investors.axt.com/Investors/news/news-details/2026/AXT-Announces-Closing-of-Public-Offering-of-Common-Stock/default.aspx"},
        {"text": "Fourth consecutive substrate price increase, with Q4 above 10%; suppliers say money alone will not get you material.", "asOf": "2026-08-17", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },
    {
      "ticker": "IQE", "name": "IQE", "layer": "materials", "hq": "GB", "listed": true,
      "what": "Compound semiconductor epiwafers (InP, GaAs) supplied to laser and RF chip makers.",
      "role": "The epitaxy step between the substrate and the laser; capacity already constrained and prices moving for a third consecutive increase.",
      "bull": "Same squeeze as AXT one step downstream, with a multi-year Tower Semiconductor deal and a quantum-dot laser purchase agreement with Quintessent.",
      "bear": "Small, historically loss-making, and the quantum-dot market it leads is tiny.",
      "watch": "Epiwafer pricing and capacity additions.",
      "facts": [
        {"text": "Announced a purchase agreement with Quintessent as quantum-dot lasers move to customer sampling.", "asOf": "2026-09-03", "source": "https://x.com/aleabitoreddit/status/2095460499769155944"},
        {"text": "Epiwafer prices moving toward a third consecutive increase; epiwafer capacity described as already constrained.", "asOf": "2026-08-25", "source": "https://x.com/aleabitoreddit/status/2092186856792506435"}
      ]
    },
    {
      "ticker": "SOI.PA", "name": "Soitec", "layer": "materials", "hq": "FR", "listed": true,
      "what": "Silicon-on-insulator wafers, including the photonics-SOI wafers silicon photonics is built on.",
      "role": "A near-monopoly input for silicon photonics, now being locked up under capacity reservation agreements.",
      "bull": "More than ten capacity reservation agreements, $200m of photonics-SOI revenue described as a floor, and FY2027 silicon-photonics revenue guided to double.",
      "bear": "The rest of the business (RF, mobile) is cyclical and weak; the photonics line is small in absolute terms.",
      "watch": "Reservation agreements converting to shipments.",
      "facts": [
        {"text": "80% of capacity reservation agreements expected within one to two weeks, more than ten in total; $200m photonics-SOI revenue described as absolutely a floor. TSMC sees silicon photonics going mainstream in 2027.", "asOf": "2026-08-31", "source": "https://x.com/aleabitoreddit/status/2094378666927239596"},
        {"text": "Guides FY2027 silicon photonics revenue to double year on year, ahead of Morgan Stanley's 60% growth projection.", "asOf": "2026-07-29", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"}
      ]
    },
    {
      "ticker": "GLW", "name": "Corning", "layer": "materials", "hq": "US", "listed": true,
      "what": "Optical fibre and specialty glass, including glass-core substrates for advanced packaging.",
      "role": "Fibre is on every list of co-packaged optics bottlenecks (TSMC's and Foxconn's), and Corning is the largest Western fibre maker. Glass substrates are the longer-dated option.",
      "bull": "Fibre demand scales with every optical link, and Citi now groups fibre with lasers as the next HBM.",
      "bear": "The glass-substrate layer has slipped: Samsung Electro-Mechanics moved its start to 2028 and SKC pushed back too.",
      "watch": "Fibre pricing and lead times; a dated glass-substrate order from a named customer.",
      "facts": [
        {"text": "Named by TSMC's VP of Advanced Packaging among the real bottlenecks to large-scale optical deployment: lasers, optical fibre, connectors and test.", "asOf": "2026-08-31", "source": "https://x.com/aleabitoreddit/status/2094298008955535500"}
      ]
    },

    {
      "ticker": "GEV", "name": "GE Vernova", "layer": "power", "hq": "US", "listed": true,
      "what": "Gas turbines plus grid equipment: substations, switchgear, transformers and HVDC.",
      "role": "One of only three suppliers of large gas turbines worldwide, with slots booked years out. The clearest listed owner of the power constraint.",
      "bull": "Data-centre electrification orders reached $2.4bn in a single quarter and turbine slots are booked into 2029-31.",
      "bear": "It sells into a shortage it cannot expand out of quickly; the multiple already prices the backlog.",
      "watch": "Turbine slot availability and pricing; grid equipment lead times.",
      "facts": [
        {"text": "Data-centre electrification orders of $2.4bn in a single quarter; large gas turbine slots booked into 2029-31 across only three suppliers. Power transformer lead times about 128 weeks, generator step-up units about 144.", "asOf": "2026-08-12", "source": "https://power2026.ai"}
      ]
    },
    {
      "ticker": "ENR.DE", "name": "Siemens Energy", "layer": "power", "hq": "DE", "listed": true,
      "what": "Gas and steam turbines, grid technology (transformers, switchgear, HVDC) and transmission equipment.",
      "role": "The second of three global large gas turbine makers, with multi-year backlogs. A direct constraint on how fast gas-fired power for AI campuses can be built.",
      "bull": "Same booked-out turbine market as GE Vernova, plus European grid spend.",
      "bear": "Execution history in wind (Gamesa) and a slower order-to-revenue cycle.",
      "watch": "Gas turbine order intake and delivery slots.",
      "facts": [
        {"text": "One of three global manufacturers, with GE Vernova and Mitsubishi Power, able to supply the large gas turbines data-centre developers need; turbine backlogs run multiple years.", "asOf": "2026-08-12", "source": "https://power2026.ai"}
      ]
    },
    {
      "ticker": "CEG", "name": "Constellation Energy", "layer": "power", "hq": "US", "listed": true,
      "what": "The largest nuclear generation fleet in the United States.",
      "role": "Hyperscalers contract directly with nuclear operators to secure firm, always-on power outside the interconnection queue.",
      "bull": "Firm carbon-free capacity under long-term agreements at prices set by scarcity.",
      "bear": "Regulatory and political risk on co-location deals; limited ability to add capacity quickly.",
      "watch": "New direct power agreements with hyperscalers and their pricing.",
      "facts": []
    },
    {
      "ticker": "BE", "name": "Bloom Energy", "layer": "power", "hq": "US", "listed": true,
      "what": "Solid-oxide fuel cells that generate power on site, independent of grid interconnection.",
      "role": "Sells a way around the interconnection queue, which is the buildout's hardest scheduling constraint.",
      "bull": "Revenue growth of 166% year on year with margins expanding, and a fivefold increase in Brookfield's financing for its fuel cells to $25bn, triggered by grid bottlenecks.",
      "bear": "Fuel-cell economics depend on gas prices and on the queue staying long.",
      "watch": "Deployments funded under the Brookfield facility.",
      "facts": [
        {"text": "Revenue up 166% year on year with expanding margins and raised 2026 guidance; grid power bottlenecks triggered a fivefold increase, to $25bn, in Brookfield's financing for its fuel cells.", "asOf": "2026-07-31", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"},
        {"text": "Situational Awareness held $1.899bn of Bloom Energy at 30 June, its third-largest position after Sandisk and Micron.", "asOf": "2026-09-02", "source": "https://x.com/aleabitoreddit/status/2095087925822190023"}
      ]
    },
    {
      "ticker": "VRT", "name": "Vertiv", "layer": "power", "hq": "US", "listed": true,
      "what": "Power and thermal management for data centres: UPS, busway, coolant distribution units and liquid-cooling loops.",
      "role": "Every megawatt a hyperscaler adds becomes heat that has to be removed; Vertiv sells the removal, and liquid cooling is now mandatory above about 100kW per rack.",
      "bull": "Content per megawatt rises with rack density.",
      "bear": "Competes with Schneider, Eaton and the hyperscalers' own designs.",
      "watch": "Orders and backlog against hyperscaler capex.",
      "facts": []
    },
    {
      "ticker": "ETN", "name": "Eaton", "layer": "power", "hq": "IE", "listed": true,
      "what": "Electrical distribution equipment: switchgear, breakers, busway and power management for data centres.",
      "role": "Sits between the grid and the rack; switchgear and breakers are on multi-quarter lead times.",
      "bull": "Electrical equipment is a capacity-constrained market with pricing power.",
      "bear": "Diversified industrial; data centre is one segment among many.",
      "watch": "Data-centre order growth and lead times.",
      "facts": []
    }
  ],

  "narratives": [
    {
      "id": "memory-squeeze",
      "title": "The memory squeeze",
      "status": "consensus",
      "summary": "HBM and then everything beneath it. Three suppliers, contract prices rising for five quarters, gross margins above 80%, and agreements that run to 2030.",
      "case": "Every accelerator needs HBM, three companies make it, and the makers have reallocated wafers away from commodity DRAM and NAND, so the shortage cascades down to DDR4 and even DDR2. Samsung has reportedly reserved 70% of capacity to 2031, SK hynix's CEO says the shortage lasts to end-2030, and NVIDIA's supply commitments jumped from $119bn to $279bn largely on memory. In China, HBM scarcity has lifted accelerator prices 20-50%.",
      "counter": "The margins are the argument against. Micron at 85% and Sandisk at 85% are cycle peaks no memory cycle has held; Sandisk says two thirds of its growth is price. SK hynix pairs discipline language with accelerating M15X and a Yongin fab in early 2027, and TrendForce already has the rate of contract-price increase slowing. The other side of the trade is showing up as gross-margin compression at NVIDIA and Broadcom. And the swing supplier is getting better: CXMT's fifth-generation platform, in mass production from September 2026, yields at least 50% more dies per wafer.",
      "signposts": ["Contract price momentum quarter on quarter (TrendForce)", "Micron fiscal Q4 on 30 September against its own $50bn and $31 EPS bar", "SK hynix and Samsung 2027 capex guides", "HBM pricing disclosed as contracted for 2027"],
      "companies": ["MU", "000660.KS", "005930.KS", "SNDK", "CXMT", "NVDA", "AVGO", "LRCX"]
    },
    {
      "id": "laser-shortage",
      "title": "Lasers and indium phosphide are the next HBM",
      "status": "building",
      "summary": "Every optical link needs an InP laser. Three firms hold most merchant capacity, one has withdrawn, and buyers now name lasers and fibre as the binding constraint on module output.",
      "case": "Broadcom's CEO says laser demand far surpasses supply while Broadcom triples capacity; Coherent has stopped selling lasers externally and will buy some in; TSMC's packaging VP and Foxconn's interconnect chairman both name lasers and fibre as the real bottleneck; Citi calls them the next HBM. Beneath the laser, InP substrate prices have risen four quarters running and Bloomberg calls the material an industry-level risk. Lumentum's margin expansion is the shortage showing up in accounts.",
      "counter": "The capacity response is dated and large: Sivers targets 100m lasers a year from Q4 2027, Broadcom is tripling, Lumentum and AAOI are expanding. Small entrants are financing the build with equity ahead of orders (Sivers, AAOI, AXT all trade below their placement prices). And the InP capacity that matters most sits in China under export permits.",
      "signposts": ["Laser ASPs through the 70-200mW range", "Capacity announcements with a customer attached, not just a date", "Chinese export permit cadence for InP", "Whether module makers pass laser cost through"],
      "companies": ["LITE", "COHR", "AAOI", "MTSI", "SIVE", "AVGO", "AXTI", "IQE", "GLW", "JBL"]
    },
    {
      "id": "copper-to-optics",
      "title": "Copper runs out; optics moves into the package",
      "status": "building",
      "summary": "Copper cannot carry the bandwidth of a 100kW rack. Pluggable optics scale first; near-packaged optics arrive late 2027-2028; co-packaged optics after.",
      "case": "Goldman lifted the optical module TAM to $148.5bn by 2028, a 115% revision. TSMC sees silicon photonics mainstream in 2027 and Soitec is signing capacity reservations for the wafers beneath it. Marvell and MACOM independently put NPO at late 2027-2028 with CPO after, which is a timeline two companies now agree on.",
      "counter": "That agreed timeline is a year later than the optics bulls had it in August, so the first-generation CPO pool is small. Meanwhile active electrical cables stretch copper's life inside the rack, and the pluggable incumbents keep the volume for longer.",
      "signposts": ["First dated NPO or CPO production win with volumes", "Optical module TAM revisions", "Photonics-SOI reservation agreements converting to shipments"],
      "companies": ["MRVL", "AVGO", "TSM", "GFS", "SOI.PA", "LITE", "COHR", "AAOI", "SIVE", "CRDO", "ANET", "ALAB"]
    },
    {
      "id": "custom-silicon",
      "title": "Custom silicon versus the GPU",
      "status": "contested",
      "summary": "Broadcom and Marvell build XPUs for Google, Meta, Microsoft and Amazon. The share shift is real; the margin on it is lower; and NVIDIA is now investing in the ASIC ecosystem itself.",
      "case": "Broadcom guides AI revenue to $230bn by FY28 and says networking grows as fast as XPUs. Marvell has Google's TPU ecosystem agreement and Microsoft's Maia ramp. Amazon is buying warrants across its silicon suppliers. Hyperscaler in-house chips take share at every generation.",
      "counter": "NVIDIA's hyperscaler revenue still rose from $43bn to $49bn in a quarter. XPU gross margin is structurally lower because memory rides inside the package. NVIDIA's $3.5bn MediaTek investment suggests it would rather shape the ASIC field than lose to it. And Broadcom's book is five customers deep.",
      "signposts": ["NVIDIA hyperscaler revenue versus Broadcom AI revenue each quarter", "A named flagship programme moving between Broadcom, Marvell and MediaTek", "Broadcom customer concentration"],
      "companies": ["NVDA", "AVGO", "MRVL", "AMD", "GOOGL", "AMZN", "MSFT", "META"]
    },
    {
      "id": "financing",
      "title": "Who is paying for the buildout",
      "status": "contested",
      "summary": "In the first half of 2026 the spend stopped being funded by operations. Alphabet raised equity, NVIDIA guaranteed its customer's leases, and the small suppliers financed capacity with dilution.",
      "case": "Alphabet's free cash flow went negative and its long-term debt doubled in six months, with $49.6bn of equity raised and a $40bn ATM signed. Amazon's first-half free cash flow was negative $27bn. NVIDIA carries $366bn of commitments including $105bn of lease guarantees for OpenAI, equity stakes in its customers, and receivables of $63bn concentrated in five names. Nebius spends 8x revenue on capex funded by convertibles; AAOI raised $1.7bn in equity in five months.",
      "counter": "The operating businesses underneath are excellent: Google Cloud up 82%, NVIDIA growing 106%, and the labs' own scenarios show the payoff arriving in 2028-2030. Capex now is the price of that. Microsoft still expects positive free cash flow. The financing is a sizing question, not a solvency one, until a lab misses a payment.",
      "signposts": ["A hyperscaler quarter with free cash flow above zero and no new issuance", "Any draw on Alphabet's $40bn ATM", "Convertible terms on the next neocloud raise", "NVIDIA receivables and customer concentration"],
      "companies": ["GOOGL", "AMZN", "NVDA", "OPENAI", "ANTHROPIC", "NBIS", "CRWV", "IREN", "AAOI", "SIVE", "AXTI", "LITE"]
    },
    {
      "id": "power-constraint",
      "title": "Power is the binding constraint",
      "status": "consensus",
      "summary": "Not chips. Transformers are quoted at 128 weeks, turbines are booked to 2029-31 across three suppliers, and Alphabet's own filing says shells and power set the 2027 ceiling.",
      "case": "Alphabet's net property and equipment rose $74.6bn in six months and the constraint it is spending to clear is physical capacity. Grid bottlenecks drove a fivefold increase in Brookfield's financing for Bloom fuel cells. Hyperscalers contract directly with nuclear operators to skip the interconnection queue, and former bitcoin miners are valued on their grid connections.",
      "counter": "The listed exposure is thin and indirect. Most of the constrained equipment (transformers, cells for backup units) is made by unlisted or Asian suppliers, and the names that do list already trade on the backlog. Demand for power is not in question; which company captures the scarcity rent is.",
      "signposts": ["Transformer and turbine lead times", "Direct power contracts signed by hyperscalers", "Interconnection queue reforms"],
      "companies": ["GEV", "ENR.DE", "CEG", "BE", "VRT", "ETN", "IREN", "GOOGL"]
    },
    {
      "id": "packaging",
      "title": "Advanced packaging is the chip bottleneck",
      "status": "consensus",
      "summary": "The accelerator die is not the constraint; joining it to its HBM is. CoWoS is booked, OSATs warn of a 20% capacity deficit by 2027, and packaging tool orders are the equipment layer's growth.",
      "case": "OSATs have told customers traditional packaging capacity could be short by more than 20% in 2027. NVIDIA is prepaying $1.5bn for Amkor's US capacity. Applied Materials raised advanced-packaging growth above 70% with discussions to 2030. TSMC is raising prices into the constraint.",
      "counter": "Capacity is being added on a known schedule by TSMC, Amkor, ASE and Intel, and the 2027 deficit warning may itself pull orders forward. Packaging shortages have resolved faster than memory ones historically.",
      "signposts": ["CoWoS and successor capacity additions with dates", "Amkor Arizona ramp", "Intel or Samsung packaging winning a named AI customer"],
      "companies": ["TSM", "AMKR", "ASX", "INTC", "AMAT", "KLAC", "NVDA"]
    },
    {
      "id": "gpu-residual",
      "title": "Do GPUs hold their value?",
      "status": "contested",
      "summary": "The neocloud bear case is that rented GPUs depreciate faster than contracts pay them off. Oracle's renewal pricing is the first realised data point against it.",
      "case": "Oracle resold all renewing GPU capacity at a 20% premium on equipment mostly four years and older. CoreWeave is still signing contracts for six-year-old A100s. Demand for any compute at all exceeds supply, so old chips clear.",
      "counter": "Two data points in a shortage. Residual values hold while capacity is scarce and collapse when it is not; the test is what old capacity fetches once 2027 supply lands. The neoclouds' financing assumes the premium persists.",
      "signposts": ["Renewal pricing on old capacity from any operator", "Utilisation disclosures", "Convertible terms, which price this risk"],
      "companies": ["ORCL", "CRWV", "NBIS", "IREN", "NVDA"]
    },
    {
      "id": "china",
      "title": "China, export controls and the upstream inputs",
      "status": "building",
      "summary": "NVIDIA guides with China at zero. China's leverage is upstream (gallium, rare earths, InP) rather than in fabrication, and the West's real monopolies are European and Japanese.",
      "case": "China reportedly halted some rare-earth shipments to the US; Japan's gallium, dysprosium, terbium and yttrium imports from China were zero in June; Reuters names indium phosphide among past targets. AXT's substrates are made in China under export permits. HBM scarcity is repricing Chinese accelerators and CXMT is scaling domestic DRAM.",
      "counter": "NVIDIA is growing 106% with China valued at zero, so any reopening is upside. The chokepoints that matter most (EUV, photoresist, photonics-SOI) sit in the Netherlands, Japan and France, outside China's reach. Substitution of Chinese inputs is slow but underway.",
      "signposts": ["Chinese export permit cadence for InP and gallium", "NVIDIA China data-centre revenue re-entering guidance", "CXMT HBM qualification"],
      "companies": ["NVDA", "AXTI", "CXMT", "ASML", "SOI.PA", "TSM", "MTSI", "INTC"]
    }
  ],

  "developments": [
    {"date": "2026-09-30", "title": "Micron reports fiscal Q4", "summary": "The largest scheduled test of the memory squeeze. Micron's own bar is $50bn revenue and $31 EPS; the number to read is gross margin against the 86% guide.", "companies": ["MU", "000660.KS", "SNDK"], "narratives": ["memory-squeeze"], "sourceType": "company", "source": "https://investors.micron.com/news/press-release/2026/Micron-Technology-to-Report-Fiscal-Fourth-Quarter-Results-on-September-30-2026/default.aspx"},
    {"date":  "2026-09-21", "title":  "Coherent launches PhotonLink with more than ten CPO and ten NPO customer engagements; revenue from Q4 2026", "summary":  "An integrated optics platform spanning lasers, silicon photonics, fibre, micro-optics, detectors, assembly and test, with anchor customers and long-term agreements in both architectures. Coherent turns its exit from merchant InP laser supply into a systems business.", "companies":  ["COHR", "LITE"], "narratives":  ["copper-to-optics", "laser-shortage"], "sourceType":  "company", "source":  "https://ir.coherent.com/news-releases/news-release-details/coherent-launches-photonlinktm-integrated-optics-platform-ai"},
    {"date":  "2026-09-21", "title":  "Korea's chip exports hit a record $34.1bn for 1-20 September, up 259%", "summary":  "Chips were about 47.8% of all Korean exports, and shipments to China more than doubled to $16.6bn. Customs data is the earliest hard read on memory volume and price each month.", "companies":  ["000660.KS", "005930.KS", "MU"], "narratives":  ["memory-squeeze"], "sourceType":  "press", "source":  "https://www.koreaherald.com/article/10880060"},
    {"date":  "2026-09-20", "title":  "CXMT puts its fifth-generation DRAM platform into mass production: at least 50% more dies per wafer", "summary":  "Quadruple patterning at an 11.95nm half-pitch, with two 24Gb LPDDR5X parts already in volume; CXMT says its process is now on par with the most advanced nodes in mass production. The swing supplier in the memory squeeze just became materially more efficient.", "companies":  ["CXMT", "MU", "000660.KS", "005930.KS"], "narratives":  ["memory-squeeze", "china"], "sourceType":  "press", "source":  "https://www.tradingview.com/news/reuters.com,2026:newsml_L6N45C00G:0-china-s-cxmt-says-new-memory-chip-platform-enters-mass-production/"},
    {"date":  "2026-09-16", "title":  "Intel CEO: Intel meets only about half of CPU demand; memory prices already up five- to sevenfold", "summary":  "Lip-Bu Tan said the squeeze now reaches the host CPU as AI shifts to inference and agents. The shortage has spread from accelerators and memory to server CPUs, and from there to the substrates they share.", "companies":  ["INTC", "AMD"], "narratives":  ["memory-squeeze", "packaging"], "sourceType":  "press", "source":  "https://www.trendforce.com/news/2026/09/16/news-intel-ceo-flags-ai-supply-squeeze-memory-prices-up-5-7x-its-cpus-meet-just-50-of-demand/"},
    {"date": "2026-09-16", "title": "Foxconn names CW lasers and fibre the biggest photonics bottleneck", "summary": "Foxconn Interconnect's chairman identified CW lasers and optical fibre as the binding constraint, and Foxconn is considering joint upstream investments to secure supply, the same pattern NVIDIA followed with Lumentum and Coherent.", "companies": ["LITE", "COHR", "GLW"], "narratives": ["laser-shortage"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2100290486569505223"},
    {"date": "2026-09-13", "title": "Oracle resold renewing GPU capacity at a 20% premium", "summary": "All GPU capacity coming up for renewal was resold above the previous contracts, on equipment mostly four years old or older. The first realised-price evidence against the rapid-depreciation bear case.", "companies": ["ORCL", "NBIS", "IREN", "CRWV"], "narratives": ["gpu-residual"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2099048356345696391"},
    {"date": "2026-09-10", "title": "HBM scarcity lifts Chinese accelerator prices 20-50%", "summary": "Huawei raised indicated pricing for the Ascend 950DT 20-50% above quotes from two months earlier and Cambricon's 690 is reported up 20-30%, both attributed to HBM cost. The memory makers are taxing everyone downstream.", "companies": ["MU", "000660.KS", "005930.KS"], "narratives": ["memory-squeeze", "china"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2097937708178186303"},
    {"date": "2026-09-09", "title": "Citi: lasers and optical fibre positioned as the next HBM", "summary": "A Citi TMT note frames lasers and fibre as the scarce inputs that will carry a scarcity premium through the optical cycle, the analogy the memory trade ran on in 2025-26.", "companies": ["LITE", "AAOI", "COHR", "SIVE", "GLW", "MTSI"], "narratives": ["laser-shortage"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2097660318369697875"},
    {"date": "2026-09-09", "title": "CIOE channel checks: Sivers has raised laser prices; 70mW the tightest grade", "summary": "Crowd-sourced checks from CIOE Shenzhen confirmed Sivers is engaged with Chinese pluggable makers and has raised prices; Innolight checks put ASPs rising across the whole 70-200mW range.", "companies": ["SIVE"], "narratives": ["laser-shortage"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2097563877273989456"},
    {"date": "2026-09-08", "title": "Goldman lifts the optical module market forecast 115% for 2028", "summary": "Revised to $67.7bn for 2026, $131.4bn for 2027 and $148.5bn for 2028, with modelled optical content per NVIDIA Rubin Ultra system raised.", "companies": ["NVDA", "LITE", "COHR", "AAOI", "FN"], "narratives": ["copper-to-optics"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2097365614402969638"},
    {"date": "2026-09-08", "title": "Amazon takes warrants over a ~$4bn Qualcomm stake tied to $60bn of milestone revenue", "summary": "Extends Amazon's pattern of holding equity in its own silicon suppliers (Alchip, Marvell, Astera Labs, Applied Optoelectronics). The cheapest diversified exposure to the custom-silicon build.", "companies": ["AMZN", "ALAB", "MRVL", "AAOI"], "narratives": ["custom-silicon"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2097321349555306512"},
    {"date": "2026-09-08", "title": "Palantir names Nebius its preferred sovereign AI infrastructure partner", "summary": "A designation that routes Palantir's government and enterprise relationships toward Nebius capacity. No contract value disclosed.", "companies": ["NBIS"], "narratives": ["financing"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2097327653116363127"},
    {"date": "2026-09-08", "title": "Intel reported to raise PC CPU prices 10% in October", "summary": "Per Digitimes. Alongside legacy memory revenue at ESMT up roughly 605% year on year, evidence that the shortage is repricing mature silicon, not only leading-edge.", "companies": ["INTC"], "narratives": ["memory-squeeze"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2097232588796780856"},
    {"date": "2026-09-07", "title": "Bloomberg: indium phosphide substrates emerging as a key risk for the semiconductor industry", "summary": "Third-party validation of the substrate chokepoint beneath the laser layer, a year after it was first argued through AXT.", "companies": ["AXTI", "IQE"], "narratives": ["laser-shortage", "china"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2096904209371427277"},
    {"date": "2026-09-07", "title": "SK hynix and Samsung stockpiles reported below ten days of supply", "summary": "KB Securities forecasts the tightest supply conditions in history for next year.", "companies": ["000660.KS", "005930.KS", "MU"], "narratives": ["memory-squeeze"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2096858276290015563"},
    {"date": "2026-09-04", "title": "China reportedly halts some rare-earth shipments to the US", "summary": "No blanket ban and no named materials. Japan's gallium, dysprosium, terbium and yttrium imports from China stood at zero in June; Shin-Etsu suspended new orders for dysprosium magnets; Reuters names InP among past targets.", "companies": ["AXTI", "LITE"], "narratives": ["china"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2095802636876619928"},
    {"date": "2026-09-04", "title": "Where the real chokepoints sit: ASML, Soitec, and a Japanese cluster", "summary": "A map of near-monopolies: ASML in EUV with Zeiss and Trumpf beneath; Soitec in photonics-SOI; Japanese firms at 90-100% share in EUV photoresist, coat and develop, mask inspection and blanks. China's leverage is upstream inputs, not fabrication.", "companies": ["ASML", "SOI.PA", "TSM", "KLAC", "LRCX"], "narratives": ["china"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2095823005595439615"},
    {"date": "2026-09-03", "title": "Sivers commits USD 30m to Glasgow for more than 100m CW DFB lasers a year", "summary": "Operational Q4 2027. Against TrendForce's estimate of about 608m units of global CW and EML capacity, a material addition, but the release states no customer commitments.", "companies": ["SIVE", "AVGO", "LITE"], "narratives": ["laser-shortage"], "sourceType": "company", "source": "https://www.sivers-semiconductors.com/press/sivers-semiconductors-invests-usd-30-million-to-expand-european-photonics-manufacturing-for-ai-datacenters/"},
    {"date": "2026-09-03", "title": "NVIDIA acquires Hugging Face for $12.93bn", "summary": "Reported rationale: 18m developers, 3m models and support for open-weight models. A platform move compared to Microsoft buying GitHub.", "companies": ["NVDA"], "narratives": [], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2095490725412733092"},
    {"date": "2026-09-03", "title": "IQE signs a purchase agreement with Quintessent as quantum-dot lasers move to sampling", "summary": "IQE positioned as the quantum-dot epitaxy leader; the market is small but the laser link is the point.", "companies": ["IQE"], "narratives": ["laser-shortage"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2095460499769155944"},
    {"date": "2026-09-02", "title": "Broadcom Q3: AI revenue $16.7bn, FY28 guided to ~$230bn, laser demand far surpassing supply", "summary": "AI semiconductor revenue up 221% and guided to $21.7bn; FY27 AI revenue about $115bn and FY28 about $230bn against a street near $180bn. Non-GAAP gross margin fell to 74.9% from 78.4%, attributed to memory content in XPUs. The CEO said laser demand far surpasses supply while Broadcom triples laser capacity.", "companies": ["AVGO", "LITE", "MRVL"], "narratives": ["custom-silicon", "laser-shortage", "memory-squeeze"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/0001730168/000173016826000076/avgo-08022026x8kxex99.htm"},
    {"date": "2026-09-02", "title": "NVIDIA: unconstrained growth would exceed 100%; 70% is what it can supply", "summary": "Told JPMorgan its revenue could more than double unconstrained; the 70% fiscal 2028 guide reflects supply. Implied FY27 revenue about $401bn and FY28 about $682bn at 70%.", "companies": ["NVDA"], "narratives": ["memory-squeeze", "packaging"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2095153855818547571"},
    {"date": "2026-09-02", "title": "Marvell at Semicon Taiwan: NPO late 2027-2028, CPO after; lasers sourced from Europe and Japan", "summary": "Marvell's SVP of optical engineering gave a transition timeline that matches MACOM's, and named Europe and Japan rather than the US as laser sourcing geographies for silicon-photonics modules.", "companies": ["MRVL", "SIVE", "LITE", "TSM"], "narratives": ["copper-to-optics", "laser-shortage"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2095102771418845551"},
    {"date": "2026-09-02", "title": "Situational Awareness 13F: Sandisk, Micron, Bloom, TSMC and Nebius the top positions", "summary": "Holdings at 30 June: SNDK $5.67bn, MU $5.57bn, BE $1.90bn, TSM $1.27bn, NBIS $1.23bn, CRWV $0.74bn. A concentrated bet on memory and power.", "companies": ["SNDK", "MU", "BE", "TSM", "NBIS", "CRWV"], "narratives": ["memory-squeeze", "power-constraint"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2095087925822190023"},
    {"date": "2026-09-01", "title": "Anthropic signs a $35bn compute deal with Lambda", "summary": "NVIDIA-backed Lambda supplies the GPUs; Hut 8 the data centres. Frontier demand keeps landing on neocloud and colocation operators rather than only the hyperscalers.", "companies": ["ANTHROPIC", "NVDA"], "narratives": ["financing"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2094585395224981709"},
    {"date": "2026-08-31", "title": "NVIDIA invests $3.5bn in MediaTek", "summary": "Read as NVIDIA networking itself into the custom-ASIC ecosystem, from Marvell to MediaTek, aligning future designs with its standards and eroding Broadcom's position.", "companies": ["NVDA", "AVGO", "MRVL"], "narratives": ["custom-silicon"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2094405648293482965"},
    {"date": "2026-08-31", "title": "Soitec: more than ten photonics-SOI capacity reservation agreements; $200m revenue a floor", "summary": "80% of the reservation agreements expected within one to two weeks. TSMC separately sees silicon photonics mainstream in 2027.", "companies": ["SOI.PA", "TSM"], "narratives": ["copper-to-optics"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2094378666927239596"},
    {"date": "2026-08-31", "title": "Samsung reportedly reserves ~70% of memory capacity through 2031 under long-term agreements", "summary": "NVIDIA, Microsoft and Google named as the main counterparties. Five years of demand visibility, if the reports are right.", "companies": ["005930.KS", "NVDA", "MSFT", "GOOGL"], "narratives": ["memory-squeeze"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2094365307876040857"},
    {"date": "2026-08-31", "title": "TSMC: the optical bottlenecks are lasers, fibre, connectors and test, not the foundry", "summary": "TSMC's VP of Advanced Packaging said foundries can scale the optical engine; the constraints on large-scale deployment lie elsewhere.", "companies": ["TSM", "LITE", "SIVE", "GLW", "COHR"], "narratives": ["copper-to-optics", "laser-shortage"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2094298008955535500"},
    {"date": "2026-08-30", "title": "Musk lists the AI buildout's failure points: transformers, wiring, liquid cooling, chillers", "summary": "None of them are chips. The list maps onto the power and cooling suppliers rather than the semiconductor chain.", "companies": ["VRT", "ETN", "GEV"], "narratives": ["power-constraint"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2094027369648681284"},
    {"date": "2026-08-30", "title": "NVIDIA projects $1.3T of hyperscaler capex in 2027", "summary": "Up from about $800bn in 2026, alongside 70% revenue growth while still capacity-constrained, against prior street expectations near 45%.", "companies": ["NVDA", "MSFT", "GOOGL", "AMZN", "META"], "narratives": ["financing"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2094019167527776711"},
    {"date": "2026-08-29", "title": "OSATs warn traditional packaging capacity could be short by more than 20% in 2027", "summary": "IC design insiders report the warning to clients; Amkor and Powertech named as beneficiaries, with Powertech's advanced packaging booked to 2030.", "companies": ["AMKR", "ASX"], "narratives": ["packaging"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2093712497949950242"},
    {"date": "2026-08-28", "title": "SK hynix CEO: the memory shortage lasts to end-2030; NVIDIA supply commitments up to $279bn on memory", "summary": "Sandisk sees structural NAND demand to 2030 at about 80% margins; Winbond is discussing allocations to 2029-30; NVIDIA describes memory pricing as extreme and still rising.", "companies": ["000660.KS", "SNDK", "NVDA"], "narratives": ["memory-squeeze"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2093252439973777674"},
    {"date": "2026-08-27", "title": "Sivers Q2: sales down 12%, pipeline up to $1.2bn, six new pluggable engagements", "summary": "Net sales SEK 53.8m and adjusted EBITDA SEK -35.5m while the opportunity pipeline grew 268% since December. Three engagements in alpha sampling, three in supply assessment. Revenue contracting while the story grows.", "companies": ["SIVE", "JBL", "GFS"], "narratives": ["laser-shortage", "financing"], "sourceType": "company", "source": "https://www.sivers-semiconductors.com/press/sivers-semiconductors-reports-q2-2026-results-as-product-growth-record-pipeline-and-customer-ramps-position-company-for-growth-acceleration/"},
    {"date": "2026-08-26", "title": "NVIDIA Q2 FY27: $96.2bn revenue, 70% growth guided for FY28, gross margin guided down", "summary": "Data centre $89.0bn; Q3 guided to $108bn with no China data-centre compute revenue assumed. Gross margin guided to 74.0% from 75.0%, the first sequential compression this cycle, as memory content per package rises. Hyperscaler revenue $48.7bn from $43.1bn.", "companies": ["NVDA", "MU", "000660.KS"], "narratives": ["memory-squeeze", "custom-silicon", "china"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000073/q2fy27pr.htm"},
    {"date": "2026-08-26", "title": "NVIDIA 10-Q: $366bn of commitments, receivables $63bn with five customers holding 70%", "summary": "Supply commitments of $92bn, $87bn and $88bn across FY27-29 for memory and manufacturing capacity, plus $29bn of cloud service agreements, $25bn of equity investments and $25bn of leases not yet commenced. Investment-grade buyers get 90-day to one-year terms.", "companies": ["NVDA", "CRWV", "NBIS"], "narratives": ["financing"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm"},
    {"date": "2026-08-24", "title": "NVIDIA's Groq3 LPX enters full production; Nebius first to deploy", "summary": "3,400 tokens per second on Gemma 4 31B at 100k context in Artificial Analysis benchmarking; Nebius gets early access as the special treatment that followed NVIDIA's investment.", "companies": ["NVDA", "NBIS"], "narratives": [], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2091909391238979970"},
    {"date": "2026-08-24", "title": "Applied Optoelectronics files a third equity raise since April: a $600m ATM", "summary": "Roughly $1.7bn raised in equity across three programmes while first-half operating cash flow was negative $73.8m. Proceeds committed only to general corporate purposes.", "companies": ["AAOI"], "narratives": ["financing", "laser-shortage"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/1158114/000110465926099685/tm2623389-1_424b5.htm"},
    {"date": "2026-08-19", "title": "Marvell and Google sign a TPU ecosystem agreement with a reported $12.2bn warrant", "summary": "Reported to span TPU compute, storage and networking with about $120bn of potential revenue through 2033. Press characterisation; not found in either company's filings.", "companies": ["MRVL", "GOOGL"], "narratives": ["custom-silicon"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2091264273007960320"},
    {"date": "2026-08-17", "title": "NVIDIA guarantees the residual value on 4.25GW of OpenAI data-centre leases, capped at $105bn", "summary": "Disclosed under Item 2.03 as an off-balance-sheet obligation, with optional credit support for 3.8GW more. On OpenAI non-payment NVIDIA pays the shortfall. Ready-for-service begins 2028.", "companies": ["NVDA", "OPENAI"], "narratives": ["financing"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/nvda-20260817.htm"},
    {"date": "2026-08-17", "title": "AXT: fourth consecutive indium phosphide substrate price increase", "summary": "Q4 increase above 10%; suppliers say money alone will not get you material. The squeeze has reached the wafer under the laser.", "companies": ["AXTI", "IQE"], "narratives": ["laser-shortage"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"},
    {"date": "2026-08-16", "title": "Applied Materials raises advanced-packaging growth guidance above 70%", "summary": "From above 50%, with customer discussions now extending to 2030. The equipment-layer confirmation of the packaging constraint.", "companies": ["AMAT"], "narratives": ["packaging"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2091909391238979970"},
    {"date": "2026-08-13", "title": "MACOM Q3: revenue up 18% sequentially, Q4 guided to $415-425m; CW laser production a potential late-2027 start", "summary": "Revenue $342.2m at 58.3% gross margin. The 75mW CW laser is still in reliability testing with near-packaged optics revenue expected from 2028: the laser programme is later than the bulls had it, while the rest of the company accelerates.", "companies": ["MTSI"], "narratives": ["laser-shortage", "copper-to-optics"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/0001493594/000149359426000036/ex99_1earningsreleaseq3fy26.htm"},
    {"date": "2026-08-12", "title": "Lumentum FY26: revenue up 83%, gross margin 28% to 42%, next quarter guided to the target model early", "summary": "Record EML shipments and initial 1.6T production; ultra-high-power CW laser demand let it raise prices. The same year carried a $7.8bn convertible extinguishment loss and a 28% rise in share count.", "companies": ["LITE"], "narratives": ["laser-shortage", "financing"], "sourceType": "company", "source": "https://investor.lumentum.com/financial-news-releases/news-details/2026/Lumentum-Announces-Fourth-Quarter-and-Full-Fiscal-Year-2026-Results/default.aspx"},
    {"date": "2026-08-12", "title": "Coherent FY26: fiscal 2027 essentially booked, long-term agreements to the end of the decade", "summary": "Q4 revenue $2.046bn, up 33.8%, at 40.2% non-GAAP gross margin. Management later confirmed it has withdrawn from merchant InP laser supply.", "companies": ["COHR"], "narratives": ["laser-shortage"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/820318/000119312526346860/d128030dex991.htm"},
    {"date": "2026-08-11", "title": "CoreWeave backlog reaches about $104bn plus $25bn of new agreements", "summary": "Excludes agreements signed in early Q3. The largest single read on frontier demand spilling past the hyperscalers.", "companies": ["CRWV"], "narratives": ["gpu-residual", "financing"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2091909391238979970"},
    {"date": "2026-08-06", "title": "Applied Optoelectronics Q2: revenue $191.9m, Q3 guided to $255-290m, three customers 92% of revenue", "summary": "Demand validated for the whole optics group. In the 10-Q: Digicomm, a cable-TV distributor, holds two thirds of receivables, which stand at 164% of quarterly revenue.", "companies": ["AAOI", "JBL", "LITE"], "narratives": ["laser-shortage", "financing"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/0001158114/000143774926026278/aaoi20260630_10q.htm"},
    {"date": "2026-08-05", "title": "Sandisk Q4: data-centre revenue up 103% sequentially, gross margin 84.6%, $14bn buyback added", "summary": "Two thirds of sequential growth was price; consumer revenue fell 32%. Minimum contracted revenue $93bn. The board is buying back stock with peak-cycle cash at peak-cycle prices.", "companies": ["SNDK"], "narratives": ["memory-squeeze"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/2023554/000162828026053346/sndkq4-26ex991xpressrelease.htm"},
    {"date": "2026-07-31", "title": "Amazon raises 2026 capex to about $220bn; not enough capacity in 2026 or 2027", "summary": "Most incoming 2027 capacity already reserved. First-half free cash flow negative $27bn.", "companies": ["AMZN"], "narratives": ["financing", "power-constraint"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"},
    {"date": "2026-07-30", "title": "Microsoft and Meta hold or raise capex; compute scarcity commanding premium offers", "summary": "Microsoft: $41bn quarterly capex, $19.6bn free cash flow, about $175bn guided, free-cash-flow positive expected in 2027. Meta narrowed its range higher to $130-145bn.", "companies": ["MSFT", "META"], "narratives": ["financing"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"},
    {"date": "2026-07-29", "title": "Alphabet Q2: Cloud up 82%, free cash flow negative, $49.6bn of equity raised", "summary": "Operating cash flow $39.07bn against capex $44.92bn; 2026 capex guidance raised to $195-205bn. Long-term debt from $46.5bn to $98.2bn in six months; a $40bn ATM signed. Net income mostly unrealised gains on equity stakes.", "companies": ["GOOGL"], "narratives": ["financing", "power-constraint"], "sourceType": "company", "source": "https://s206.q4cdn.com/479360582/files/doc_financials/2026/q2/2026q2-alphabet-earnings-release.pdf"},
    {"date": "2026-07-29", "title": "AMD Q2: data centre 58% of revenue, gross margin 53.8%, Helios in full production", "summary": "Revenue $11.54bn, up 50%. Data-centre revenue $6.7bn with segment operating income $2.1bn from a loss a year earlier. Long-term accelerator TAM raised to $220bn by 2030.", "companies": ["AMD"], "narratives": ["custom-silicon"], "sourceType": "filing", "source": "https://www.sec.gov/Archives/edgar/data/2488/000000248826000123/amd-20260627.htm"},
    {"date": "2026-07-29", "title": "CXMT lists in Shanghai with a 470% first-day move", "summary": "China's largest DRAM maker valued near $487bn at the close from $85.5bn. The swing supplier in the memory squeeze is now public and expensively priced.", "companies": ["CXMT"], "narratives": ["memory-squeeze", "china"], "sourceType": "analyst", "source": "https://x.com/aleabitoreddit/status/2092723047107355133"},
    {"date": "2026-07-03", "title": "TrendForce: 3Q26 DRAM contract prices up 13-18%, NAND up 10-15%, pace moderating", "summary": "The shortage holds, but weaker consumer demand and a higher base slow the rate of increase. The second derivative of memory pricing has turned.", "companies": ["MU", "SNDK", "000660.KS"], "narratives": ["memory-squeeze"], "sourceType": "press", "source": "https://www.trendforce.com/presscenter/news/20260703-13134.html"},
    {"date": "2026-07-01", "title": "Sivers places 12.3m shares at SEK 57 in an oversubscribed directed issue", "summary": "About SEK 700m raised from institutions on the capacity story. Ten weeks later the shares traded near half that price.", "companies": ["SIVE"], "narratives": ["financing"], "sourceType": "company", "source": "https://www.sivers-semiconductors.com/press/sivers-semiconductors-has-resolved-on-a-directed-share-issue-of-shares-amounting-to-approximately-sek-700-million/"}
  ]
};
