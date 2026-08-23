import sys, os
# Root folder ko path me add karo taaki main.py mile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app

# Vercel isi 'app' ko dhoondta hai
# Bas itna hi kaafi hai!
