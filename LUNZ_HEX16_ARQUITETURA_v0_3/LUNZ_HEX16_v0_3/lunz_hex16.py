#!/usr/bin/env python3
"""LUNZ HEX-16 architectural simulator v0.2.

Standard-library-only analytical model. It is not RTL, cycle-accurate silicon,
or a calibrated power/area model. Cache hit rates are estimated from a capacity
scaling law anchored at a 16 KiB baseline and must be replaced by trace-driven
cache results once real workloads are available.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import argparse
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple


class PowerState(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    SLEEP = "sleep"
    DEEP_SLEEP = "deep-sleep"


@dataclass(frozen=True)
class CoreSpec:
    core_id: int
    row: int
    col: int


@dataclass
class CoreConfig:
    issue_width: int = 1
    l1_size_kb: int = 16  # each of L1I and L1D, per core
    l1_instruction_hit_at_16kb: float = 0.98
    l1_data_hit_at_16kb: float = 0.92
    cache_capacity_exponent: float = 0.50
    cache_line_bytes: int = 64
    cache_ways: int = 4
    base_ipc: float = 0.85
    active_static_w: float = 0.18
    dynamic_w_at_3ghz: float = 0.42
    idle_w: float = 0.07
    sleep_w: float = 0.012
    deep_sleep_w: float = 0.002


@dataclass
class MemoryConfig:
    l1_hit_cycles: int = 1
    l2_hit_cycles_at_3ghz: int = 12
    dram_cycles_at_3ghz: int = 120
    l2_hit_rate: float = 0.85
    dram_energy_nj: float = 35.0


@dataclass
class NoCConfig:
    hop_cycles_at_3ghz: int = 2
    link_energy_nj_per_hop: float = 0.18


@dataclass
class WorkloadConfig:
    total_instructions_m: float = 160.0
    memory_ops_fraction: float = 0.25
    communication_fraction: float = 0.05
    parallel_efficiency: float = 0.90
    burstiness: float = 0.20


@dataclass
class SimulatorConfig:
    cores: int = 16
    frequency_ghz: float = 3.0
    min_frequency_ghz: float = 0.5
    max_frequency_ghz: float = 3.5
    recommended_frequency_ghz: float = 3.0
    voltage_at_3ghz: float = 0.90
    voltage_exponent: float = 0.55
    core: CoreConfig = field(default_factory=CoreConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    noc: NoCConfig = field(default_factory=NoCConfig)
    workload: WorkloadConfig = field(default_factory=WorkloadConfig)
    seed: int = 7


_POSITIONS: List[Tuple[int, int]] = [
    (0, 0), (0, 1), (0, 2),
    (1, 0), (1, 1), (1, 2), (1, 3),
    (2, 0), (2, 1), (2, 2), (2, 3), (2, 4),
    (3, 1), (3, 2), (3, 3), (3, 4),
]


def build_topology() -> Tuple[List[CoreSpec], Dict[int, List[int]]]:
    cores = [CoreSpec(i, r, c) for i, (r, c) in enumerate(_POSITIONS)]
    by_pos = {p: i for i, p in enumerate(_POSITIONS)}
    neighbors: Dict[int, List[int]] = {i: [] for i in range(len(cores))}
    for i, (r, c) in enumerate(_POSITIONS):
        if r % 2 == 0:
            offsets = [(0, -1), (0, 1), (-1, -1), (-1, 0), (1, -1), (1, 0)]
        else:
            offsets = [(0, -1), (0, 1), (-1, 0), (-1, 1), (1, 0), (1, 1)]
        for dr, dc in offsets:
            p = (r + dr, c + dc)
            if p in by_pos:
                neighbors[i].append(by_pos[p])
        neighbors[i].sort()
    return cores, neighbors


def shortest_path_hops(src: int, dst: int, neighbors: Dict[int, List[int]]) -> int:
    if src == dst:
        return 0
    queue = [src]
    dist = {src: 0}
    head = 0
    while head < len(queue):
        u = queue[head]
        head += 1
        for v in neighbors[u]:
            if v in dist:
                continue
            dist[v] = dist[u] + 1
            if v == dst:
                return dist[v]
            queue.append(v)
    raise RuntimeError("Topology is disconnected")


def all_pairs_hops(neighbors: Dict[int, List[int]]) -> List[List[int]]:
    n = len(neighbors)
    return [[shortest_path_hops(i, j, neighbors) for j in range(n)] for i in range(n)]


def cache_hit_rate(size_kb: int, baseline_hit_rate: float, cfg: CoreConfig) -> float:
    """Capacity-only estimate, not a trace-derived hit rate.

    Miss rate follows miss(C) = miss(16 KiB) * (16/C)^alpha, capped at 75%.
    """
    if size_kb <= 0:
        raise ValueError("L1 size must be positive")
    baseline_miss = 1.0 - baseline_hit_rate
    scaled_miss = min(0.75, baseline_miss * (16.0 / size_kb) ** cfg.cache_capacity_exponent)
    return 1.0 - scaled_miss


def cache_geometry(size_kb: int, line_bytes: int = 64, ways: int = 4) -> dict:
    if size_kb <= 0 or line_bytes <= 0 or ways <= 0:
        raise ValueError("cache size, line size, and associativity must be positive")
    total_bytes = size_kb * 1024
    if total_bytes % line_bytes:
        raise ValueError("cache capacity must be divisible by cache line size")
    lines = total_bytes // line_bytes
    sets, remainder = divmod(lines, ways)
    return {
        "size_kib": size_kb,
        "line_bytes": line_bytes,
        "ways": ways,
        "lines": lines,
        "sets": sets if remainder == 0 else None,
        "valid_geometry": remainder == 0,
        "power_of_two_sets": remainder == 0 and sets > 0 and (sets & (sets - 1)) == 0,
    }


def scaled_voltage(freq_ghz: float, cfg: SimulatorConfig) -> float:
    ratio = max(freq_ghz / cfg.recommended_frequency_ghz, 0.25)
    v = cfg.voltage_at_3ghz * (0.82 + 0.18 * ratio ** cfg.voltage_exponent)
    return min(max(v, 0.65), 1.10)


def scaled_dynamic_power(freq_ghz: float, cfg: SimulatorConfig) -> float:
    f_ratio = freq_ghz / cfg.recommended_frequency_ghz
    v_ratio = scaled_voltage(freq_ghz, cfg) / cfg.voltage_at_3ghz
    return cfg.core.dynamic_w_at_3ghz * (v_ratio ** 2) * f_ratio


def cycles_to_ns(cycles: float, freq_ghz: float) -> float:
    return cycles / freq_ghz


@dataclass
class CoreResult:
    core_id: int
    instructions: float
    compute_cycles: float
    memory_cycles: float
    communication_cycles: float
    active_time_ns: float
    energy_mj: float
    instruction_l1_hit_rate: float
    data_l1_hit_rate: float
    instruction_l1_misses: float
    data_l1_misses: float
    dram_misses: float
    state: PowerState


@dataclass
class SimulationResult:
    config: SimulatorConfig
    avg_hops: float
    max_hops: int
    wall_time_us: float
    aggregate_instructions_m: float
    aggregate_cycles_m: float
    throughput_gips: float
    total_energy_mj: float
    average_power_w: float
    energy_per_instruction_nj: float
    active_cores: int
    core_results: List[CoreResult]

    def to_dict(self) -> dict:
        return {
            "version": "0.2",
            "frequency_ghz": self.config.frequency_ghz,
            "recommended_frequency_ghz": self.config.recommended_frequency_ghz,
            "l1_size_kib_per_cache_per_core": self.config.core.l1_size_kb,
            "l1_instruction_hit_rate_estimate": cache_hit_rate(self.config.core.l1_size_kb, self.config.core.l1_instruction_hit_at_16kb, self.config.core),
            "l1_data_hit_rate_estimate": cache_hit_rate(self.config.core.l1_size_kb, self.config.core.l1_data_hit_at_16kb, self.config.core),
            "avg_hops": self.avg_hops,
            "max_hops": self.max_hops,
            "wall_time_us": self.wall_time_us,
            "aggregate_instructions_m": self.aggregate_instructions_m,
            "aggregate_cycles_m": self.aggregate_cycles_m,
            "throughput_gips": self.throughput_gips,
            "total_energy_mj": self.total_energy_mj,
            "average_power_w": self.average_power_w,
            "energy_per_instruction_nj": self.energy_per_instruction_nj,
            "active_cores": self.active_cores,
        }


def _validate_config(cfg: SimulatorConfig) -> None:
    if cfg.cores != 16:
        raise ValueError("LUNZ HEX-16 simulator currently models exactly 16 cores")
    if not (cfg.min_frequency_ghz <= cfg.frequency_ghz <= cfg.max_frequency_ghz):
        raise ValueError(f"frequency must be between {cfg.min_frequency_ghz} and {cfg.max_frequency_ghz} GHz")
    if cfg.core.l1_size_kb not in (14, 16):
        raise ValueError("L1 size experiment currently supports 14 or 16 KiB per cache per core")
    w = cfg.workload
    if w.total_instructions_m <= 0:
        raise ValueError("workload instructions must be positive")
    if not (0 <= w.memory_ops_fraction <= 1):
        raise ValueError("memory operation fraction must be between 0 and 1")
    if not (0 <= w.communication_fraction <= 1):
        raise ValueError("communication fraction must be between 0 and 1")
    if not (0 <= w.parallel_efficiency <= 1):
        raise ValueError("parallel efficiency must be between 0 and 1")
    if not (0 <= w.burstiness < 1):
        raise ValueError("burstiness must be in [0, 1)")
    if not (0 < cfg.memory.l2_hit_rate <= 1):
        raise ValueError("L2 hit rate must be in (0, 1]")
    for rate in (cfg.core.l1_instruction_hit_at_16kb, cfg.core.l1_data_hit_at_16kb):
        if not (0 <= rate <= 1):
            raise ValueError("baseline cache hit rates must be in [0, 1]")


def simulate(cfg: SimulatorConfig) -> SimulationResult:
    _validate_config(cfg)
    rng = random.Random(cfg.seed)
    cores, neighbors = build_topology()
    hops = all_pairs_hops(neighbors)
    pair_count = len(cores) * (len(cores) - 1)
    avg_hops = sum(sum(row) for row in hops) / pair_count
    max_hops = max(max(row) for row in hops)

    wl = cfg.workload
    total_i = wl.total_instructions_m * 1_000_000.0
    # Jitter changes per-core distribution without silently changing total work.
    factors = [1.0 + rng.uniform(-wl.burstiness, wl.burstiness) for _ in cores]
    factor_sum = sum(factors)
    instructions_by_core = [total_i * f / factor_sum for f in factors]

    f = cfg.frequency_ghz
    v = scaled_voltage(f, cfg)
    dynamic_w = scaled_dynamic_power(f, cfg)
    static_w = cfg.core.active_static_w * (0.65 + 0.35 * (v / cfg.voltage_at_3ghz))
    l2_cycles = cfg.memory.l2_hit_cycles_at_3ghz * (3.0 / f)
    dram_cycles = cfg.memory.dram_cycles_at_3ghz * (3.0 / f)
    noc_hop_cycles = cfg.noc.hop_cycles_at_3ghz * (3.0 / f)
    i_hit = cache_hit_rate(cfg.core.l1_size_kb, cfg.core.l1_instruction_hit_at_16kb, cfg.core)
    d_hit = cache_hit_rate(cfg.core.l1_size_kb, cfg.core.l1_data_hit_at_16kb, cfg.core)
    expected_hops = max(1.0, avg_hops * (1.0 - 0.35 * min(1.0, 2.0 / max(avg_hops, 1.0))))

    results: List[CoreResult] = []
    total_core_energy_mj = 0.0
    wall_time_ns = 0.0
    for core, instructions in zip(cores, instructions_by_core):
        data_ops = instructions * wl.memory_ops_fraction
        compute_ops = instructions - data_ops
        comm_ops = instructions * wl.communication_fraction * max(0.0, 1.0 - wl.parallel_efficiency * 0.05)
        compute_cycles = compute_ops / max(cfg.core.base_ipc * cfg.core.issue_width, 0.1)

        i_misses = instructions * (1.0 - i_hit)
        d_hits = data_ops * d_hit
        d_misses = data_ops - d_hits
        all_l1_misses = i_misses + d_misses
        l2_misses = all_l1_misses * (1.0 - cfg.memory.l2_hit_rate)
        l2_hits = all_l1_misses - l2_misses
        memory_cycles = (
            d_hits * cfg.memory.l1_hit_cycles
            + l2_hits * l2_cycles
            + l2_misses * dram_cycles
        )
        communication_cycles = comm_ops * expected_hops * noc_hop_cycles
        total_cycles = compute_cycles + memory_cycles + communication_cycles
        active_time_ns = cycles_to_ns(total_cycles, f)
        wall_time_ns = max(wall_time_ns, active_time_ns)
        active_energy_mj = (dynamic_w + static_w) * (active_time_ns / 1e9) * 1000.0
        dram_energy_mj = l2_misses * cfg.memory.dram_energy_nj / 1e6
        noc_energy_mj = comm_ops * expected_hops * cfg.noc.link_energy_nj_per_hop / 1e6
        energy_mj = active_energy_mj + dram_energy_mj + noc_energy_mj
        total_core_energy_mj += energy_mj
        results.append(CoreResult(
            core_id=core.core_id,
            instructions=instructions,
            compute_cycles=compute_cycles,
            memory_cycles=memory_cycles,
            communication_cycles=communication_cycles,
            active_time_ns=active_time_ns,
            energy_mj=energy_mj,
            instruction_l1_hit_rate=i_hit,
            data_l1_hit_rate=d_hit,
            instruction_l1_misses=i_misses,
            data_l1_misses=d_misses,
            dram_misses=l2_misses,
            state=PowerState.ACTIVE,
        ))

    tail_ns = wall_time_ns * 0.08
    sleep_energy_mj = len(cores) * cfg.core.sleep_w * (tail_ns / 1e9) * 1000.0
    total_energy_mj = total_core_energy_mj + sleep_energy_mj
    wall_time_us = wall_time_ns / 1000.0
    throughput_gips = (total_i / 1e9) / (wall_time_ns / 1e9)
    average_power_w = total_energy_mj / 1000.0 / (wall_time_us / 1e6)
    energy_per_instruction_nj = (total_energy_mj * 1e6) / total_i
    aggregate_cycles_m = sum(r.compute_cycles + r.memory_cycles + r.communication_cycles for r in results) / 1e6
    return SimulationResult(
        config=cfg,
        avg_hops=avg_hops,
        max_hops=max_hops,
        wall_time_us=wall_time_us,
        aggregate_instructions_m=sum(instructions_by_core) / 1e6,
        aggregate_cycles_m=aggregate_cycles_m,
        throughput_gips=throughput_gips,
        total_energy_mj=total_energy_mj,
        average_power_w=average_power_w,
        energy_per_instruction_nj=energy_per_instruction_nj,
        active_cores=len(cores),
        core_results=results,
    )


def render_topology() -> str:
    cores, neighbors = build_topology()
    rows: Dict[int, List[CoreSpec]] = {}
    for c in cores:
        rows.setdefault(c.row, []).append(c)
    out = ["LUNZ HEX-16 topology (up to 6 local neighbors per node)\n"]
    for r in sorted(rows):
        indent = "  " if r in (1, 3) else ""
        out.append(indent + "  ".join(f"[{c.core_id:02d}]" for c in rows[r]))
    out.append("\nNeighbor table:")
    for i in range(len(cores)):
        out.append(f"  C{i:02d}: " + ", ".join(f"C{n:02d}" for n in neighbors[i]))
    return "\n".join(out)


def print_result(result: SimulationResult) -> None:
    c = result.config
    i_hit = cache_hit_rate(c.core.l1_size_kb, c.core.l1_instruction_hit_at_16kb, c.core)
    d_hit = cache_hit_rate(c.core.l1_size_kb, c.core.l1_data_hit_at_16kb, c.core)
    geom = cache_geometry(c.core.l1_size_kb, c.core.cache_line_bytes, c.core.cache_ways)
    print("\n=== LUNZ HEX-16 SIMULATION v0.2 ===")
    print(f"Clock:                       {c.frequency_ghz:.2f} GHz")
    print(f"Recommended clock:           {c.recommended_frequency_ghz:.2f} GHz")
    print(f"Voltage model:               {scaled_voltage(c.frequency_ghz, c):.3f} V")
    print(f"Cores active:                {result.active_cores}/16")
    print(f"L1I/L1D size per core:       {c.core.l1_size_kb}/{c.core.l1_size_kb} KiB")
    print(f"Estimated L1I hit rate:      {i_hit * 100:.3f}%")
    print(f"Estimated L1D hit rate:      {d_hit * 100:.3f}%")
    print(f"Cache geometry (4-way):      {geom['lines']} lines/cache, {geom['sets']} sets/cache")
    print(f"Power-of-two set count:      {'yes' if geom['power_of_two_sets'] else 'no'}")
    print(f"Average NoC hops:            {result.avg_hops:.3f}")
    print(f"Maximum NoC hops:            {result.max_hops}")
    print(f"Workload:                    {result.aggregate_instructions_m:.1f} M instructions")
    print(f"Aggregate cycles:            {result.aggregate_cycles_m:.2f} M cycles")
    print(f"Wall time:                   {result.wall_time_us:.3f} us")
    print(f"Throughput:                  {result.throughput_gips:.3f} GIPS")
    print(f"Estimated energy:            {result.total_energy_mj:.3f} mJ")
    print(f"Average power:               {result.average_power_w:.3f} W")
    print(f"Energy/instruction:          {result.energy_per_instruction_nj:.4f} nJ")
    print("Note: cache hit rates and power are simplified estimates, not silicon measurements.")


def cache_sweep(base: SimulatorConfig) -> List[dict]:
    rows: List[dict] = []
    print("\n=== L1 CACHE CAPACITY SWEEP ===")
    print("L1 KiB  I-hit %  D-hit %  Time(us)  GIPS    Power(W)  Energy(mJ)  nJ/inst  DRAM misses(M)")
    print("-" * 100)
    for size in (14, 16):
        core = CoreConfig(**{**asdict(base.core), "l1_size_kb": size})
        cfg = SimulatorConfig(**{**base.__dict__, "core": core})
        r = simulate(cfg)
        dram_misses = sum(item.dram_misses for item in r.core_results) / 1e6
        row = {
            "l1_kib_per_cache_per_core": size,
            "l1_instruction_hit_estimate": cache_hit_rate(size, core.l1_instruction_hit_at_16kb, core),
            "l1_data_hit_estimate": cache_hit_rate(size, core.l1_data_hit_at_16kb, core),
            "total_l1_capacity_kib": 16 * 2 * size,
            "dram_misses_m": dram_misses,
            **r.to_dict(),
        }
        rows.append(row)
        print(f"{size:>6}  {row['l1_instruction_hit_estimate']*100:>7.3f}  {row['l1_data_hit_estimate']*100:>7.3f}  "
              f"{r.wall_time_us:>8.3f}  {r.throughput_gips:>5.3f}  {r.average_power_w:>8.3f}  "
              f"{r.total_energy_mj:>10.3f}  {r.energy_per_instruction_nj:>7.4f}  {dram_misses:>14.5f}")
    row14, row16 = rows
    saved_kib = 16 * 2 * (16 - 14)
    delta_energy_mj = row14["total_energy_mj"] - row16["total_energy_mj"]
    print(f"\nHEX-14 saves {saved_kib} KiB of total L1 capacity across the chip (12.5%).")
    print(f"HEX-14 minus HEX-16 estimated total energy: {delta_energy_mj:+.3f} mJ (positive means HEX-14 is higher).")
    # Approximate break-even power savings per KiB of removed L1 capacity, using active core time.
    r14_cfg = SimulatorConfig(**{**base.__dict__, "core": CoreConfig(**{**asdict(base.core), "l1_size_kb": 14})})
    r14 = simulate(r14_cfg)
    sum_active_s = sum(x.active_time_ns for x in r14.core_results) / 1e9
    break_even_mw_per_kib = ((delta_energy_mj / 1000.0) / (sum_active_s * 4.0)) * 1000.0 if sum_active_s else math.nan
    print(f"Break-even cache-power reduction: ~{break_even_mw_per_kib:.3f} mW per saved KiB during active time.")
    print("Interpretation: 14 KiB reduces capacity, but this model does not calibrate SRAM leakage/area; do not choose an energy winner from this alone.")
    return rows


def frequency_sweep(base: SimulatorConfig, freqs: List[float]) -> List[dict]:
    print("\n=== FREQUENCY SWEEP ===")
    print("Freq(GHz)  Time(us)  Throughput(GIPS)  Power(W)  Energy(mJ)  nJ/inst")
    print("-" * 76)
    rows = []
    for f in freqs:
        cfg = SimulatorConfig(**{**base.__dict__, "frequency_ghz": f})
        r = simulate(cfg)
        rows.append(r.to_dict())
        print(f"{f:>8.2f}  {r.wall_time_us:>8.3f}  {r.throughput_gips:>16.3f}  {r.average_power_w:>8.3f}  {r.total_energy_mj:>10.3f}  {r.energy_per_instruction_nj:>8.4f}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="LUNZ HEX-16 architectural simulator v0.2")
    parser.add_argument("--freq", type=float, default=3.0, help="CPU frequency in GHz (default: 3.0)")
    parser.add_argument("--l1-kib", type=int, choices=(14, 16), default=16,
                        help="capacity of each L1I and L1D cache per core")
    parser.add_argument("--workload-m", type=float, default=160.0, help="workload size in million instructions")
    parser.add_argument("--memory-frac", type=float, default=0.25, help="fraction of instructions with data-memory operations")
    parser.add_argument("--comm-frac", type=float, default=0.05, help="communication fraction")
    parser.add_argument("--seed", type=int, default=7, help="deterministic workload seed")
    parser.add_argument("--topology", action="store_true", help="print the hexagonal topology")
    parser.add_argument("--sweep", action="store_true", help="run a 0.5 to 3.5 GHz frequency sweep")
    parser.add_argument("--cache-sweep", action="store_true", help="compare 14 KiB and 16 KiB L1 caches")
    parser.add_argument("--json", type=Path, help="write base simulation result as JSON")
    args = parser.parse_args()

    core = CoreConfig(l1_size_kb=args.l1_kib)
    cfg = SimulatorConfig(
        frequency_ghz=args.freq,
        seed=args.seed,
        core=core,
        workload=WorkloadConfig(
            total_instructions_m=args.workload_m,
            memory_ops_fraction=args.memory_frac,
            communication_fraction=args.comm_frac,
        ),
    )
    if args.topology:
        print(render_topology())
    result = simulate(cfg)
    print_result(result)
    if args.sweep:
        frequency_sweep(cfg, [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5])
    if args.cache_sweep:
        cache_sweep(cfg)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(f"\nJSON saved to: {args.json}")


if __name__ == "__main__":
    main()
