# data_processor/transformers/base.py

from .enrollment_transformers import EnrollmentTransformers
from .removal_transformers import RemovalTransformers
from .forward_exam_transformers import ForwardExamTransformers
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


class DataTransformer:
    """
    Main transformer class that delegates to specialized transformation modules.
    
    This class serves as the entry point for all transformations and routes requests
    to the appropriate specialized transformer based on the transformation type.
    """
    
    def __init__(self, request):
        self.request = request
        self.enrollment = EnrollmentTransformers(request)
        self.removal = RemovalTransformers(request)
        self.forward_exam = ForwardExamTransformers(request)
    
    def apply_transformation(self, transformation_type):
        """
        Apply the selected transformation type by delegating to the appropriate module.
        
        Args:
            transformation_type: String identifier for the transformation to apply
            
        Returns:
            bool: True if transformation succeeded, False otherwise
        """
        # Enrollment transformations (6 types)
        if transformation_type == 'Statewide V01':
            return self.enrollment.transform_statewide()
        elif transformation_type == 'Tri-County':
            return self.enrollment.apply_tri_county_layer_transformation()
        elif transformation_type == 'County-Layer':
            return self.enrollment.apply_county_layer_transformation()
        elif transformation_type == 'Metopio Statewide':
            return self.enrollment.transform_Metopio_StateWideLayer()
        elif transformation_type == 'Zipcode':
            return self.enrollment.transforms_Metopio_ZipCodeLayer()
        elif transformation_type == 'City-Town':
            return self.enrollment.transform_Metopio_CityLayer()
        
        # Removal/Discipline transformations (6 types)
        elif transformation_type == 'Statewide-Removal':
            return self.removal.transform_Statewide_Removal_OPTIMIZED()
        elif transformation_type == 'Tricounty-Removal':
            return self.removal.transform_Tri_County_Removal_OPTIMIZED()
        elif transformation_type == 'County-Removal':
            return self.removal.transform_County_Layer_Removal()
        elif transformation_type == 'Zipcode-Removal':
            return self.removal.transform_Zipcode_Layer_Removal_OPTIMIZED()
        elif transformation_type == 'City-Removal':
            return self.removal.transform_City_Layer_Removal()
        elif transformation_type == 'combined':
            return self.removal.transform_combined_removal()
        
        # Forward Exam transformations (6 types)
        elif transformation_type == 'ForwardExam-Statewide':
            return self.forward_exam.transform_ForwardExam_Statewide()
        elif transformation_type == 'ForwardExam-TriCounty':
            return self.forward_exam.transform_ForwardExam_TriCounty()
        elif transformation_type == 'ForwardExam-County':
            return self.forward_exam.transform_ForwardExam_CountyLayer()
        elif transformation_type == 'ForwardExam-Zipcode':
            return self.forward_exam.transform_ForwardExam_ZipcodeLayer()
        elif transformation_type == 'ForwardExam-City':
            return self.forward_exam.transform_ForwardExam_CityLayer()
        elif transformation_type == 'ForwardExam-Combined':
            return self.forward_exam.transform_ForwardExam_Combined()
        
        else:
            messages.error(self.request, f'Unknown transformation type: {transformation_type}')
            return False
