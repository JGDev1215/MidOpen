
def simulate_equalization_and_snapping(num_weights, slider_step=0.000001):
    print(f"Simulating for {num_weights} weights with step {slider_step}")
    
    # Equalize logic from pages/1_Admin_Settings.py
    equal_weight = 1.0 / num_weights
    equalized_weights = []
    remaining = 1.0
    
    for i in range(num_weights):
        if i == num_weights - 1:
            w = round(remaining, 6)
            equalized_weights.append(w)
        else:
            w = round(equal_weight, 6)
            equalized_weights.append(w)
            remaining -= w
            
    print(f"Equalized weights (sum={sum(equalized_weights)}): {equalized_weights}")
    
    # Simulate slider snapping
    snapped_weights = []
    for w in equalized_weights:
        # Streamlit slider snapping logic approximation: round to nearest step
        # actually it might be floor or round. usually round.
        # step = 0.0001. 
        # val = round(val / step) * step
        snapped = round(w / slider_step) * slider_step
        snapped_weights.append(snapped)
        
    total_snapped = sum(snapped_weights)
    print(f"Snapped weights: {snapped_weights}")
    print(f"Total snapped: {total_snapped:.10f}")
    
    diff = abs(total_snapped - 1.0)
    print(f"Diff: {diff:.10f}")
    
    is_valid = diff <= 0.0001
    print(f"Valid (<= 0.0001): {is_valid}")
    return is_valid

# Test with 15 weights (UK100)
print("--- UK100 (15 weights) ---")
simulate_equalization_and_snapping(15)

# Test with 20 weights (US100)
print("\n--- US100 (20 weights) ---")
simulate_equalization_and_snapping(20)

# Test with 3 weights (Simple case)
print("\n--- Simple (3 weights) ---")
simulate_equalization_and_snapping(3)
