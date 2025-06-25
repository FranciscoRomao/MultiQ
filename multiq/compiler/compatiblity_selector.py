import random
import math
import copy
from typing import List, Optional, Tuple, Dict, Any, Callable
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit
from qiskit.dagcircuit.dagnode import DAGOpNode, DAGInNode, DAGOutNode
from qiskit.circuit import CommutationChecker, CircuitInstruction
from multiq.compiler.planner import Planner, MultiQConfig, Tile
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit import transpile
from mqt import qcec
import logging
import os

logger = logging.getLogger("multiq")

class CircuitSASelector:
    
    def __init__(self, 
                 config: MultiQConfig,
                 multi_circuit_prob: float = 0.3):
        """        
        Args:
            initial_temperature: Starting temperature for annealing
            final_temperature: Ending temperature (stopping criterion)
            cooling_rate: Rate at which temperature decreases (0 < rate < 1)
            max_iterations: Maximum total iterations
            max_iterations_per_temp: Maximum iterations at each temperature
        """
        self.config = config
        self.bin_costs = []
        self.positions = []  # List[List[List[int]]] - bin, row, column (tile indices)
        
        # SA parameters
        self.initial_temperature = config.initial_temperature
        self.final_temperature = config.final_temperature
        self.cooling_rate = config.cooling_rate
        self.max_iterations = config.max_iterations
        self.max_iterations_per_temp = config.max_iterations_per_temp

        self.bin_counter = 0
        
        # Initialize commutation checker
        self.checker = CommutationChecker()
        
    def select(self, 
               tiles: List[Tile], 
               seed: Optional[int] = None) -> List[QuantumCircuit]:

        self.tiles = tiles
        self.merge_circuits = merge_circuits
        self.split_dag_into_layers = split_dag_into_layers
        self.circuit_layer_cost = circuit_layer_cost
        self.window = self.config.layer_split_window

        if seed is not None:
            random.seed(seed)

        # Initialize positions and perform first fit
        self.positions = []
        self.bin_costs = []
        self.bin_counter = self._first_fit_distribution()

        logger.debug(f"Initial bin count: {self.bin_counter}")

        # Calculate initial costs for all bins
        for i in range(self.bin_counter):
            self.bin_costs.append(self._evaluate_bin_cost(i))

        current_cost = sum(self.bin_costs)

        #self._create_new_bin()

        best_cost = current_cost
        best_positions = copy.deepcopy(self.positions)
        
        temperature = self.initial_temperature
        iteration = 0
        total_accepted = 0
        total_rejected = 0
        neighbor_generation_failures = 0

        # Statistics tracking
        cost_history = [current_cost]
        temperature_history = [temperature]
        acceptance_history = []
        
        logger.info(f"Starting layout bin packing with SA")
        logger.info("-" * 50)
        logger.debug(f"Initial temperature: {temperature}")
        logger.debug(f"Initial cost: {current_cost}")
        logger.debug(f"Number of bins: {self.bin_counter}")
        logger.debug(f"Starting optimization with SA...")
        
        while (temperature > self.final_temperature and iteration < self.max_iterations):
            
            temp_accepted = 0
            temp_rejected = 0
            temp_generation_failures = 0
            
            # Run multiple iterations at current temperature
            for temp_iter in range(self.max_iterations_per_temp):
                iteration += 1
                
                # Generate neighbor solution
                logger.debug(f"Iteration {iteration}: Generating neighbor at T={temperature:.2f}")
                changed_bins = self._generate_neighbor(temperature, seed)
                
                if changed_bins is None:
                    temp_generation_failures += 1
                    neighbor_generation_failures += 1
                    if temp_generation_failures % 10 == 0:
                        logger.debug(f"Warning: {temp_generation_failures} neighbor generation failures at T={temperature:.2f}")
                    continue
                
                # Evaluate neighbor cost (only changed bins)
                try:
                    delta_cost = self._evaluate_delta_cost(changed_bins)
                    changed_bins = self._remove_empty_bins(changed_bins)
                    neighbor_cost = current_cost + delta_cost
                    logger.debug(f"Iteration {iteration}: Neighbor cost = {neighbor_cost:.3f}, Δ = {delta_cost:.3f}")
                    logger.debug(f"Changed bins: {changed_bins}")
                except Exception as e:
                    logger.warning(f"Warning: Cost evaluation failed at iteration {iteration}: {e}")
                    temp_rejected += 1
                    continue
                
                # Calculate acceptance probability
                if delta_cost < 0:
                    # Better solution - always accept
                    accept = True
                    acceptance_prob = 1.0
                else:
                    # Worse solution - accept with probability based on temperature
                    if temperature > 0:
                        acceptance_prob = math.exp(-delta_cost / temperature)
                        accept = random.random() < acceptance_prob
                    else:
                        accept = False
                        acceptance_prob = 0.0
                
                if accept:
                    current_cost = neighbor_cost
                    # Update bin costs for changed bins
                    for bin_idx in changed_bins:
                        self.bin_costs[bin_idx] = self._evaluate_bin_cost(bin_idx)
                    temp_accepted += 1
                    
                    # Update best solution if necessary
                    if current_cost < best_cost:
                        best_positions = copy.deepcopy(self.positions)
                        best_cost = current_cost
                        logger.info(f"New best solution at iteration {iteration}: cost = {best_cost:.3f} (Δ = {delta_cost:.3f})")
                else:
                    # Reject: revert changes
                    logger.debug(f"-------Iteration {iteration}: Rejecting neighbor with Δ = {delta_cost:.3f}, acceptance prob = {acceptance_prob:.3f}")
                    self._revert_last_move()
                    temp_rejected += 1
                
                # Record statistics
                cost_history.append(current_cost)
                acceptance_history.append(acceptance_prob if delta_cost >= 0 else 1.0)
                
                # Early stopping if we haven't accepted anything in a while
                if temp_accepted == 0 and temp_iter > self.max_iterations_per_temp // 2:
                    break
            
            total_accepted += temp_accepted
            total_rejected += temp_rejected
            
            # Cool down
            temperature *= self.cooling_rate
            temperature_history.append(temperature)
            
            if iteration % 100 == 0:
                acceptance_rate = temp_accepted / max(temp_accepted + temp_rejected, 1)
                logger.debug(f"Iter {iteration:4d}: T={temperature:7.3f}, Current={current_cost:6.3f}, "
                            f"Best={best_cost:6.3f}, Accept={acceptance_rate:.3f}, "
                            f"Failures={temp_generation_failures}")
        
        # Restore best solution
        self.positions = best_positions
        
        # Compile optimization statistics
        stats = {
            'total_iterations': iteration,
            'total_accepted': total_accepted,
            'total_rejected': total_rejected,
            'neighbor_generation_failures': neighbor_generation_failures,
            'final_temperature': temperature,
            'cost_history': cost_history,
            'temperature_history': temperature_history,
            'acceptance_history': acceptance_history,
            'initial_cost': cost_history[0],
            'final_cost': current_cost,
            'best_cost': best_cost,
            'improvement': cost_history[0] - best_cost,
            'improvement_percentage': (cost_history[0] - best_cost) / cost_history[0] * 100 if cost_history[0] > 0 else 0
        }
        
        overall_acceptance = total_accepted / max(total_accepted + total_rejected, 1)
        logger.info("-" * 50)
        logger.info(f"  Optimization complete!")
        logger.info(f"  Results:")
        logger.info(f"   Initial cost: {stats['initial_cost']:.3f}")
        logger.info(f"   Best cost: {best_cost:.3f}")
        logger.info(f"   Improvement: {stats['improvement']:.3f} ({stats['improvement_percentage']:.1f}%)")
        logger.info(f"   Total iterations: {iteration}")
        logger.info(f"   Overall acceptance rate: {overall_acceptance:.3f}")
        logger.info(f"   Neighbor generation failures: {neighbor_generation_failures}")

        best_positions = self._convert_tile_idx_to_tile()
        
        return best_positions
    
    def _convert_tile_idx_to_tile(self) -> Tile:
        """Converts the last positions list with tile indices to a list of tile objects."""

        if not self.positions:
            logger.error("No positions available to convert to tiles")
            raise RuntimeError("No positions to convert")

        tile_positions = []
        for bin_rows in self.positions:
            tile_positions.append([])
            for row in bin_rows:
                #tile_positions[-1].append([])  # Create a new row in the bin
                for tile_idx in row:
                        tile_positions[-1].append(self.tiles[tile_idx])
        
        return tile_positions

    def _first_fit_distribution(self) -> int:
        """
        Distribute the tiles into bins in a first fit manner.
        Returns the number of bins created.
        """
        bin_counter = 0
        
        for tile_idx, tile in enumerate(self.tiles):
            # Try to fit in existing bins
            fitted = False
            for bin_idx in range(bin_counter):
                if self._simple_fit_check(tile_idx, bin_idx, insert=True):
                    fitted = True
                    break
            
            # If it doesn't fit in any existing bin, create a new one
            if not fitted:
                self._create_new_bin()
                if self._simple_fit_check(tile_idx, bin_counter, insert=True):
                    bin_counter += 1
                else:
                    raise RuntimeError(f"Tile {tile_idx} cannot fit in any bin, QPU is too small")
        
        return bin_counter
    
    def _remove_empty_bins(self, changed_bins: List[int]) -> List[int]:
        """Remove empty bins from the positions list."""

        empty_bin = None
        
        for i,bin_idx in enumerate(changed_bins):
            if self.positions[changed_bins[i]] == [[],[]]:
                empty_bin = bin_idx
                changed_bins.pop(i)
                continue

        # There can only be one empty bin at a time, so we can safely only pop the first one
        if empty_bin:
            self.bin_costs.pop(empty_bin)
            self.positions.pop(empty_bin)

            changed_bins = [b - 1 if b > empty_bin else b for b in changed_bins]
            
            # Update bin counter
            self.bin_counter = len(self.positions)
        
        if self.bin_counter == 0:
            logger.error("All bins are empty after removal, consider re-evaluating tile distribution.")
            raise RuntimeError("No bins left after removing empty bins")
        
        return changed_bins
    
    def _create_new_bin(self):
        """Create a new empty bin with the grid structure."""
        new_bin = [[] for _ in range(self.config.grid_rows)]
        self.positions.append(new_bin)
    
    def _simple_fit_check(self, tile_idx: int, bin_idx: int, insert: bool = False) -> bool:
        """
        Check if a tile can fit in a specific bin and place it if possible.
        Returns True if fitted, False otherwise.
        """
        tile = self.tiles[tile_idx]
        
        # Ensure bin exists
        if len(self.positions) <= bin_idx:
            logger.error(f"Bin index {bin_idx} out of range. Current bins: {len(self.positions)}")
            return False
        
        # Try to fit in each row of the bin
        for row_idx in range(self.config.grid_rows):
            # Calculate current width usage in this row
            current_width = sum(
                self.tiles[existing_tile_idx].architecture.arch_range[1][0] 
                for existing_tile_idx in self.positions[bin_idx][row_idx]
            )
            
            # Check if tile fits in this row
            tile_width = tile.architecture.arch_range[1][0]
            if current_width + tile_width <= self.config.qpu_width:
                if insert:
                    # Place the tile in this row
                    self.positions[bin_idx][row_idx].append(tile_idx)
                return True
        
        return False  # Tile did not fit in any row of the bin
    
    def _simple_bin_fit_check(self, tile_idx: int, bin_idx: int, insert:False) -> bool:
        """
        Check if a tile can fit in a specific bin and place it if possible.
        Returns True if fitted, False otherwise.
        """
        tile = self.tiles[tile_idx]
        
        # Ensure bin exists
        if len(self.positions) <= bin_idx:
            logger.error(f"Bin index {bin_idx} out of range. Current bins: {len(self.positions)}")
            return False
        
        # Try to fit in each row of the bin
        for row_idx in range(self.config.grid_rows):
            # Calculate current width usage in this row
            current_width = sum(
                self.tiles[existing_tile_idx].architecture.arch_range[1][0] 
                for existing_tile_idx in self.positions[bin_idx][row_idx]
            )
            
            # Check if tile fits in this row
            tile_width = tile.architecture.arch_range[1][0]
            if current_width + tile_width <= self.config.qpu_width:
                return True
        
        return False  # Tile did not fit in any row of the bin
    
    def _simple_row_fit_check(self, tile_idx: int, bin_idx: int, row_idx: int) -> bool:
        """
        Check if a tile can fit in a specific row of a bin.
        Returns True if it fits, False otherwise.
        """
        tile = self.tiles[tile_idx]
        
        # Calculate current width usage in this row
        current_width = sum(
            self.tiles[existing_tile_idx].architecture.arch_range[1][0] 
            for existing_tile_idx in self.positions[bin_idx][row_idx]
        )
        
        # Check if tile fits in this row
        tile_width = tile.architecture.arch_range[1][0]
        return current_width + tile_width <= self.config.qpu_width
    
    def _evaluate_bin_cost(self, bin_idx: int) -> float:
        """Merge all circuits in a bin and evaluate the cost."""

        tiles = [self.tiles[tile_idx] 
                   for row in self.positions[bin_idx] 
                   for tile_idx in row]
        circuits = [tiles[i].circuit for i in range(len(tiles)) if tiles[i].circuit is not None]
        
        if not circuits:
            logger.debug(f"Bin {bin_idx} is empty, cost is zero.")
            return 0.0
            #raise ValueError("Cannot evaluate cost for empty bin")
        
        if len(circuits) == 1:
            merged_circuit = circuits[0]
        else:
            merged_circuit = self.merge_circuits(circuits)
        
        merged_dag = circuit_to_dag(merged_circuit)
        layers = self.split_dag_into_layers(merged_dag, self.window)

        entanglement_layers = 0
        
        for layer_nodes in layers:
            if any(i.num_qubits > 1 for i in layer_nodes):  # Fixed: should be > 1, not > 0
                entanglement_layers += 1
        
        #layers_cost = self.circuit_layer_cost(layers)
        
        # This is the minimum number of layers needed to execute the merged circuit
        # equivalent to the longest circuit execution 
        min_layers = max([tiles.best_nlayers for tiles in tiles if tiles.best_nlayers is not None])

        summed_layout_width = sum([i.architecture.arch_range[1][0] for i in tiles])
        avg_layout_width = summed_layout_width / len(self.positions[bin_idx])
        
        # Unused qpu width
        unused_width = self.config.qpu_width * self.config.grid_rows - summed_layout_width
        
        # The layout width normalization benefits bins with many larger layout and give a bad score to bins with smaller layout
        # This is because smaller layout can be used to fit more circuits in the same bin (in a balanced distribution)
        return (len(layers) + entanglement_layers)/min_layers * self.config.perf_weight_selector + unused_width/avg_layout_width * (1-self.config.perf_weight_selector)
    
    def _evaluate_delta_cost(self, changed_bins: List[int]) -> float:
        """
        Calculate the change in cost for only the changed bins.
        """
        delta_cost = 0.0
        
        for bin_idx in changed_bins:
            old_cost = self.bin_costs[bin_idx]
            new_cost = self._evaluate_bin_cost(bin_idx)
            delta_cost += new_cost - old_cost
        
        return delta_cost
    
    def _generate_neighbor(self, temperature: float, seed: Optional[int] = None) -> Optional[List[int]]:
        """
        Generates a random neighboring state by either moving a circuit to another bin or swapping two circuits.
        Returns list of changed bin indices, or None if generation failed.
        """
        if seed is not None:
            random.seed(seed)

        num_tiles = len(self.tiles)
        if num_tiles == 0:
            return None

        # Store original state for potential reversion
        self._previous_positions = copy.deepcopy(self.positions)

        # Decide on move type based on temperature
        temp_ratio = temperature / self.initial_temperature

        move_probability = temp_ratio * 0.5  # High temp = higher swap probability
        create_bin_probability = temp_ratio * 0.3  # High temp = higher bin creation probability

        try:
            rand_val = random.random()

            # This means that with initial temperature, we have a 30% chance to create a new bin,
            # and a 50%+30% chance of moving a single circuit, otherwise we just swap tiles which is more times valid than moving a single circuit
            # When the temperature gets to near zero the chance to create a new bin goes to zero and the move and swap probabilities become 100%
            if rand_val < create_bin_probability:
                # Create new bin operation
                return self._move_to_new_bin()
            elif rand_val < move_probability + create_bin_probability:
                # Swap move: exchange positions of two tiles
                return self._circuit_swap()
            else:
                # Move: relocate a single tile (without creating new bins)
                return self._circuit_move()
        except Exception as e:
            logger.debug(f"Neighbor generation failed: {e}")
            # self._revert_last_move()
            return None
    
    def _circuit_move(self) -> List[int]:
        """
        Move a random circuit from one bin to another.
        Returns list of affected bin indices.
        """
        # Find all tiles and their current positions
        tile_positions = []
        for bin_idx, bin_rows in enumerate(self.positions):
            for row_idx, row in enumerate(bin_rows):
                for tile_idx in row:
                    tile_positions.append((tile_idx, bin_idx, row_idx))
        
        if not tile_positions:
            logger.error("No tiles available to move")
            raise RuntimeError("No tiles to move")
        
        # Select random tile to move
        tile_idx, from_bin, from_row = random.choice(tile_positions)

        # Store original state for potential reversion
        #self._previous_positions = copy.deepcopy(self.positions)
        
        # Remove tile from current position
        self.positions[from_bin][from_row].remove(tile_idx)
        
        bins = [b for b in range(len(self.positions)) if b != from_bin]
        
        # Choose target bin (prefer different bin)
        if len(self.positions) > 1:
            to_bin = random.choice(bins)
        
            if self._simple_fit_check(tile_idx, to_bin, insert=True):
                # Success - return affected bins
                affected_bins = [from_bin, to_bin] if from_bin != to_bin else [from_bin]
                return list(set(affected_bins))
        
        # Restore bin state if placement failed
        self.positions[from_bin][from_row].append(tile_idx)
        
    def _circuit_swap(self) -> List[int]:
        """
        Swap positions of two random circuits.
        If valid returns list of affected bin indices.
        """
        # Find all tiles and their positions
        tile_positions = []
        for bin_idx, bin_rows in enumerate(self.positions):
            for row_idx, row in enumerate(bin_rows):
                for tile_idx in row:
                    tile_positions.append((tile_idx, bin_idx, row_idx))
        
        if len(tile_positions) < 2:
            raise RuntimeError("Need at least 2 tiles to swap")
        
        # Select two different tiles
        tile1_data, tile2_data = random.sample(tile_positions, 2)
        tile1_idx, bin1, row1 = tile1_data
        tile2_idx, bin2, row2 = tile2_data
        
        # Remove both tiles
        self.positions[bin1][row1].remove(tile1_idx)
        self.positions[bin2][row2].remove(tile2_idx)

        if self._simple_fit_check(tile1_idx, bin2) and self._simple_fit_check(tile2_idx, bin1):
            # Both tiles fit in the swapped positions
            self.positions[bin1][row1].append(tile2_idx)
            self.positions[bin2][row2].append(tile1_idx)
            affected_bins = [bin1, bin2] if bin1 != bin2 else [bin1]
            return list(set(affected_bins))
        else:
            self.positions[bin1][row1].append(tile1_idx)
            self.positions[bin2][row2].append(tile2_idx)
            return None  # Swap not valid, revert changes

        ## Swap positions
        #self.positions[bin1][row1].append(tile2_idx)
        #self.positions[bin2][row2].append(tile1_idx)
        #
        ## Check if swap is valid (capacity constraints)
        #if (self._check_bin_capacity(bin1) and self._check_bin_capacity(bin2)):
        #    affected_bins = [bin1, bin2] if bin1 != bin2 else [bin1]
        #    return list(set(affected_bins))
        #else:
        #    # Revert swap
        #    self.positions[bin1][row1].remove(tile2_idx)
        #    self.positions[bin2][row2].remove(tile1_idx)
        #    self.positions[bin1][row1].append(tile1_idx)
        #    self.positions[bin2][row2].append(tile2_idx)
        #    raise RuntimeError("Swap violates capacity constraints")

    def _move_to_new_bin(self) -> List[int]:
        """
        Create a new bin and move a random tile to it.
        Returns list of affected bin indices.
        """
        # Find all tiles and their current positions
        tile_positions = []
        for bin_idx, bin_rows in enumerate(self.positions):
            for row_idx, row in enumerate(bin_rows):
                for tile_idx in row:
                    tile_positions.append((tile_idx, bin_idx, row_idx))
    
        if not tile_positions:
            raise RuntimeError("No tiles to move to new bin")
    
        # Select random tile to move
        tile_idx, from_bin, from_row = random.choice(tile_positions)
    
        # Remove tile from current position
        self.positions[from_bin][from_row].remove(tile_idx)
    
        # Create new bin
        self._create_new_bin()
        new_bin_idx = len(self.positions) - 1
        self.bin_counter += 1
    
        # Place tile in new bin
        if self._simple_fit_check(tile_idx, new_bin_idx, insert=True):
            # Add cost for new bin
            #self.bin_costs.append(self._evaluate_bin_cost(new_bin_idx))
            self.bin_costs.append(0.0)  # Initial cost is zero, will be evaluated later)
            return [from_bin, new_bin_idx]
        else:
            # Revert: put tile back and remove new bin
            self.positions[from_bin][from_row].append(tile_idx)
            self.positions.pop()
            self.bin_counter -= 1
            raise RuntimeError("Failed to place tile in new bin")

    def _revert_last_move(self):
        """Revert to the previously stored state."""
        if hasattr(self, '_previous_positions'):
            self.positions = self._previous_positions

def circuit_layer_cost(circuit_layers: list) -> List[int]:
    """
    Calculate the cost of a circuit based on the number of layers.
    This computes the number of parallelizable layers assuming single qubit gates can be executed in parallel
     as well as multi-qubit gates, but multi-qubit gates cannot be executed in parallel with single qubit gates.
    The cost is the number of layers needed to execute the circuit plus the number of entanglement layers
    """
    entanglement_layers = 0
    for layer_nodes in circuit_layers:
        if any(i.num_qubits > 1 for i in layer_nodes):  # Fixed: should be > 1, not > 0
            entanglement_layers += 1

    return [len(circuit_layers), entanglement_layers]

def merge_circuits(circuits: list):
    assert len(circuits) >= 1, "At least one circuit is required to merge."

    if len(circuits) == 1:
        return circuits[0]

    new_circuit: QuantumCircuit = circuits[0].copy()

    for i in range(1, len(circuits)):
        circuit2 = circuits[i]
        new_circuit_copy = new_circuit.copy()
        
        # Create a new quantum circuit with enough qubits and classical bits
        total_qubits = new_circuit.num_qubits + circuit2.num_qubits
        total_clbits = new_circuit.num_clbits + circuit2.num_clbits

        new_circuit = QuantumCircuit(total_qubits, total_clbits)

        # Map circuit1's qubits and clbits into the new circuit
        new_circuit.compose(
            new_circuit_copy,
            qubits=range(new_circuit_copy.num_qubits),
            clbits=range(new_circuit_copy.num_clbits),
            inplace=True
        )

        # Map circuit2's qubits and clbits into the new circuit
        new_circuit.compose(
            circuit2,
            qubits=range(new_circuit_copy.num_qubits, total_qubits),
            clbits=range(new_circuit_copy.num_clbits, total_clbits),
            inplace=True
        )
    
    return new_circuit

def split_dag_into_layers(dag: DAGCircuit, window) -> list:
    removed_nodes = []
    layers = []
    dag_layers = [list(layer) for layer in dag.multigraph_layers()]  # Convert to lists
    layers_to_remove = []

    # Remove DAGInNode and DAGOutNode from the layers
    for layer in dag_layers:
        indexes_to_remove = []
        for index, node in enumerate(layer):
            if isinstance(node, DAGInNode):
                removed_nodes.append(node)
                indexes_to_remove.append(index)
            elif isinstance(node, DAGOutNode):
                indexes_to_remove.append(index)
        
        # Remove in reverse order to maintain indices
        for index in reversed(indexes_to_remove):
            layer.pop(index)
    
        if len(layer) == 0:
            layers_to_remove.append(layer)
    
    # Remove empty layers
    for layer in layers_to_remove:
        dag_layers.remove(layer)
    
    index = 0

    while len(dag_layers) > 0:
        window_slice = fetch_window_from_zero(dag_layers, window)
        
        # Starting a new layer
        current_layer = []
        multi_qubit_layer = False
        single_qubit_layer = False

        for curr_index, layer in enumerate(window_slice):
            
            # Sort by number of qubits to prioritize single qubit gates
            if any(node.num_qubits == 1 for node in layer):
                layer.sort(key=lambda x: x.num_qubits)

            for node in layer:
                # If the current layer is empty, add the first node
                if len(current_layer) == 0:
                    current_layer.append(node)
                    dag_layers[index + curr_index].remove(node) 
                    removed_nodes.append(node)
                
                    if node.num_qubits == 1:
                        single_qubit_layer = True
                    else:
                        multi_qubit_layer = True
                    continue
                
                # Check compatibility with current layer type
                if multi_qubit_layer and node.num_qubits == 1:
                    continue
                elif single_qubit_layer and node.num_qubits > 1:
                    continue

                # Check dependencies
                if any(pre_node in current_layer for pre_node in dag.predecessors(node)):
                    continue

                # Check if all predecessors were already executed
                if any(pre_node not in removed_nodes for pre_node in dag.predecessors(node)):
                    continue
                
                # Node is compatible - add it
                current_layer.append(node)
                dag_layers[index + curr_index].remove(node)
                removed_nodes.append(node)

        layers.append(current_layer)

        # Remove empty layers
        while index < len(dag_layers) and len(dag_layers[index]) == 0:
            dag_layers.pop(index)
            
    return layers

def fetch_window_from_zero(array, window) -> list:
    """Fetch a window slice from the beginning of the array."""
    end_index = min(window, len(array))
    return copy.deepcopy(array[0:end_index])