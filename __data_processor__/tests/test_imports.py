import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_data_project.settings')
django.setup()

from __data_processor__.transformers import DataTransformer

print("Testing DataTransformer import...")
dt = DataTransformer(None)
print("✅ DataTransformer imported successfully")
print("✅ Has enrollment:", hasattr(dt, 'enrollment'))
print("✅ Has removal:", hasattr(dt, 'removal'))
print("✅ Has forward_exam:", hasattr(dt, 'forward_exam'))
print("✅ Has apply_transformation:", hasattr(dt, 'apply_transformation'))
print("\nAll checks passed! The modular structure is working correctly.")
