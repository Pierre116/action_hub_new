"""
Flask dev server launcher.
Run this file to start the ActionHub development server.
"""
import os
import sys

# Change to action_hub directory
os.chdir(os.path.join(os.path.dirname(__file__), 'action_hub'))

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'action_hub'))

if __name__ == "__main__":
    from actionhub import create_app
    
    print("=" * 50)
    print("ActionHub Development Server")
    print("=" * 50)
    print()
    
    app = create_app()
    
    print(f"Registered blueprints: {list(app.blueprints.keys())}")
    print()
    print("Starting server on http://localhost:5000")
    print("Press CTRL+C to stop")
    print()
    
    app.run(host="0.0.0.0", port=5000, use_reloader=False)
