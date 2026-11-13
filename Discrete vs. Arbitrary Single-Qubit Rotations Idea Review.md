# Discrete vs. Arbitrary Single-Qubit Rotations: Idea Review

Nov 12, 2026 · @Francisco Romão

## Summary

The idea was to synthesize single-qubit gates from a small set of discrete, tightly calibrated rotations chosen for the highest cumulative fidelity, in the hope of beating arbitrary-angle pulses on neutral-atom (and ion) hardware. We concluded it is not worth pursuing as stated: with free virtual Z rotations, one arbitrary pulse already needs less pulse area than any exact discrete decomposition, a simple error model shows no clear fidelity win for discrete gates, and fault-tolerant stacks only need Clifford gates anyway. The evidence is a simplified simulation plus published benchmarks, not a head-to-head experiment, so treat the verdict as strong but not final.

## The idea

Neutral-atom (and ion) hardware can calibrate a few rotation angles very tightly, which may give higher fidelity than an arbitrary-angle pulse. Given a set of discrete angles and phases, each with a hardware-benchmarked fidelity, find the gate sequence that reaches a target single-qubit gate with the highest cumulative fidelity.

Formally this is a shortest-path problem with edge weight −log F per primitive, plus an approximation-error term when the target is only reachable approximately. It extends the 2019 minimal-gate-count problem from "fewest pieces" to "lowest total infidelity".

Extensions we considered:

- Discrete phase as well as discrete angle, for hardware that supports rotations about the Rxy plane at set phases.
- Variational circuits, where a precomputed table of sequences would avoid recompiling each step.
- A hybrid: replace a run of arbitrary rotations with a slightly longer discrete sequence plus one arbitrary correction pulse at the end.

## Related work

The closest paper is [Minimal nonorthogonal gate decomposition for qubits with limited control](https://arxiv.org/abs/1810.07569) (Zhang et al., PRA 2019), which gives the minimal number of non-orthogonal rotations for any single-qubit gate. We did not find a later paper that adds hardware fidelity weights or discrete angle sets.

Other relevant work:

- **Free-axis and analytic variants:** the Hamada (2014) and Shim et al. (2013) results on minimal decompositions, as cited in the review [From Bits to Qubits](https://arxiv.org/pdf/2609.08058).
- **Cost-weighted synthesis:** Clifford+T synthesis with per-gate costs, e.g. "Cost-optimal single-qubit gate synthesis in the Clifford hierarchy" (2020), and Kliuchnikov et al., "Shorter quantum circuits via single-qubit gate approximation" (2023).
- **Residual absorption:** [Optimal Approximation of Single Qubit Rotations within a Quantum Circuit](https://arxiv.org/pdf/2605.09671) approximates a central rotation and absorbs the residual into neighboring rotations, the same trick as our hybrid idea but for T-count.
- **Parametrized Clifford circuits:** [van de Wetering et al. (2023)](https://arxiv.org/pdf/2401.12877) and [Vandaele et al. (2024)](https://arxiv.org/pdf/2407.07846) minimize the number of parametrized rotations.
- **Composite pulses:** BB1 and SCROFULOUS ([Cummins, Llewellyn and Jones](https://arxiv.org/abs/quant-ph/0208092)) are the standard robust pulses; both appear in neutral-atom experiments below.

These were found in web searches. We read abstracts and excerpts, not full texts.

## Hardware evidence

We found no paper that compares discrete and arbitrary angles on the same neutral-atom hardware. Published numbers come from different machines and protocols: Clifford randomized benchmarking (discrete angles) and Haar-random benchmarking (arbitrary angles). At the best labs the two land close together.

| Source | Benchmarked gates | Result | Avg. pulse area per gate |
| --- | --- | --- | --- |
| [Harvard/QuEra, Nature 2023](https://www.nature.com/articles/s41586-023-06481-y) | Haar-random rotations, two Z rotations + arbitrary BB1 pulse | 99.97% | BB1 adds a \~4π correction (our calculation) |
| [Atom Computing, Yb-171](https://arxiv.org/abs/2411.11708) | Clifford RB | 99.963% per Clifford | — |
| [Atom Computing/Microsoft, 256 Yb qubits](https://arxiv.org/html/2411.11822v3) | Clifford RB | 6.7×10⁻⁴ error per Clifford (an earlier version reported 0.15%) | — |
| [Caltech, 6100 atoms](https://arxiv.org/pdf/2403.12021) | Clifford RB with SCROFULOUS | — | 2.02π |
| [Rb-85 array](https://arxiv.org/pdf/2506.16974) | Clifford RB, no virtual Z, SCROFULOUS | F = 0.999653 | 4.46π |
| [Harvard fault-tolerant architecture](https://www.researchgate.net/publication/397467634_A_fault-tolerant_neutral-atom_architecture_for_universal_quantum_computation) | Local X(θ) rotations | \~99.9%; calibration drift adds 0.05–0.1% error | — |

Figures come from search-result excerpts and were not re-checked against the full papers.

## Analysis

On hardware with free virtual Z, any single-qubit gate needs only one arbitrary X pulse, or exactly two calibrated π/2 pulses; the discrete route is therefore not an approximation problem at all.

**Virtual Z.** A Z rotation is a frame change: the angle is added to the phase of later pulses, so it costs no time and no pulse. Its error does not depend on the angle chosen, unlike pulse area, which needs analog calibration per value. So discrete phases buy nothing where phase is free.

**Exact decompositions.** Every single-qubit gate equals Rz · Rx(β) · Rz (one pulse of area β) or Rz · √X · Rz · √X · Rz (two π/2 pulses). The mean area of a Haar-random gate is π/2 for the first and always π for the second. Averaged over the 24 Cliffords, bare pulses average 0.5π; SCROFULOUS pulses average 2.02π, matching the Caltech figure above. Merging consecutive gates on a qubit also collapses the hybrid idea, because each qubit needs one SU(2) between entangling gates.

**Simulation.** We simulated a quasi-static relative amplitude error (σ\_ε) and detuning (σ\_δ as a fraction of the Rabi frequency), with free Z and Haar-averaged targets. It covers coherent errors only: no dephasing during pulses, scattering, pulse-shape effects or crosstalk. Both composite sequences reproduced the ideal gates exactly at zero error. Values are average gate infidelity.

| Strategy | Mean area | ε = 1% | δ = 2% of Ω | ε = δ = 3% |
| --- | --- | --- | --- | --- |
| Arbitrary, bare | 0.5π | 4.9e-5 | 1.3e-4 | 7.4e-4 |
| Arbitrary, BB1 | 4.5π | 2e-11 | 1.3e-4 | 3.2e-4 |
| 2× bare π/2 (exact) | π | 8.2e-5 | 4.0e-4 | 1.6e-3 |
| 2× SCROFULOUS π/2 (exact) | 4.56π | 3e-8 | 3.6e-3 | 7.9e-3 |
| Clifford, SCROFULOUS | 2.02π | 3e-8 | 9.7e-4 | 2.2e-3 |

Three results follow:

- For an arbitrary gate, BB1 (4.5π) and the exact discrete SCROFULOUS version (4.56π) cost almost the same area, so an area-limited incoherent floor is about equal. BB1 wins on coherent error.
- SCROFULOUS is about 7× worse than a bare pulse when detuning dominates, while BB1 matches bare.
- Discrete bare π/2 pairs beat bare arbitrary pulses only if the arbitrary-angle amplitude error is about 1.3× larger (1.7× when detuning dominates). No paper we found reports per-angle calibration error, so this break-even cannot be checked.

## Why we are not pursuing it

Three reasons, in order of weight:

1. **Free Z removes the problem.** The discrete alternative is exact with two π/2 pulses, so there is no synthesis question left. A single arbitrary pulse averages half the area of that pair.
2. **No clear fidelity win.** Neutral-atom errors mostly scale with pulse time (dephasing, scattering). Composite pulses add area, and BB1 arbitrary gates (99.97% reported) already match the best Clifford benchmarks (about 99.96% to 99.97%) within a gap smaller than the differences between machines.
3. **QEC does not need it.** A fault-tolerant stack runs on Clifford gates and magic states. Arbitrary angles are synthesized into Clifford+T at the logical level, where the cost is T-count, not physical pulse fidelity, and cost-weighted synthesis already exists there. With virtual Z, S and T cost nothing physically, so only H-like pulses matter.

The main uncertainty is calibration: if each arbitrary angle drifts or is calibrated worse than π and π/2 on a given platform, discrete gates could win, but we found no data on this.

## What might survive, and open questions

A narrower idea is still open: a compiler that chooses the physical implementation of each Clifford (bare, SCROFULOUS, BB1-style) from benchmarked error budgets. The best choice depends on the platform: the Caltech array averages 2.02π per Clifford with virtual Z, the Rb-85 array 4.46π without it, and our model suggests SCROFULOUS can hurt when detuning dominates. It would apply to neutral atoms and ions.

Open questions:

- How large is per-angle calibration error versus π and π/2 on real Yb Raman hardware? Interleaved RB or XEB at a few angles would answer it.
- Is the incoherent floor (dephasing, scattering) high enough to hide every coherent difference in the table above?
- Does hardware-aware composite-pulse selection already exist for neutral atoms or ions? We have not searched for this yet.
