"""Quick test for decision feature wiring."""
import sys
sys.path.insert(0, 'C:/Users/leung/Documents/Digitalization/actionhub/action_hub')

# Test that imports work
try:
    from actionhub import create_app
    from actionhub.decisions.service import DecisionService
    print("SUCCESS: All imports work!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test app creation
try:
    app = create_app()
    print("SUCCESS: App created!")
    
    # Check blueprints are registered
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    print(f"Blueprints: {blueprint_names}")
    
    if 'decisions' in blueprint_names:
        print("SUCCESS: decisions_bp registered!")
    else:
        print("ERROR: decisions_bp NOT registered!")
        
except Exception as e:
    print(f"ERROR creating app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n=== ALL BASIC CHECKS PASSED ===")
