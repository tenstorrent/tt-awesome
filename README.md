# tt-awesome
A curated collection of awesome demos, tools, projects, and resources built by and for the Tenstorrent ecosystem.


### University of Rome
New research paper alert: Masters Thesis on Collective Operations on Wormhole n150 (Sapienza University of Rome)
Charles Heron, a master’s student supervised by Prof. Daniele De Sensi at Sapienza University of Rome, has completed an impressive thesis implementing and benchmarking five allreduce algorithms (Swing, Recursive Doubling, Bandwidth Optimal, Latency Optimal, and Shared Memory) on the Tenstorrent Wormhole n150 using TT-Metal.

Key Findings
The Bandwidth Optimal algorithm achieved the best performance across all tested vector sizes, approaching within 2× of theoretical optimal utilization.Swing Allreduce, though designed for toroidal networks, underperformed slightly due to hidden node topology effects unique to Wormhole’s mix of compute and DRAM Tensix tiles.Results were highly consistent across 20 runs — a testament to stable synchronization and low OS interference.The implementation demonstrated that TT-Metal can effectively express optimized, parallel compute+NoC workloads, though documentation gaps and hardware resets presented hurdles.

Details https://tenstorrent.slack.com/archives/C033K1XJGP5/p1762250605037429

### Cegep Sherbrooke
We are an electrical engineering department and one of our specialization is networking and telecommunication. The goal for the quietbox is two fold: I want to run a local LLM which will be an assistant for student without having to manage personal information on public servers and our networking specialization will train and implement a vision model in an industrial environment.

For now I've just ran tt-metalium-models
tests and it's working.

Julien Bosco | Enseignant

Coordonnateur du programme Technologie du génie électrique : réseaux et télécommunications

Département des Technologies du génie électrique

