from rest_framework import serializers
from django.core.cache import cache
from .models import (
    Appointment, Vitals, LabResult, MedicalReport, BlogPost, BlogCategory,
    TestRequest, VitalRequest, Assignment,
)
from users.models import Profile
from users.serializers import ProfileSerializer
import logging

logger = logging.getLogger(__name__)


def _safe_url(image_field) -> str | None:
    """
    Return the storage-backend URL for an ImageField value, or None.

    Delegates to the storage backend's .url property:
      - S3Boto3Storage  → pre-signed HTTPS URL (works with private buckets)
      - FileSystemStorage → /media/path/to/file (local dev)

    Never constructs URLs manually — that bypassed signing and broke
    against private S3 buckets (the default since April 2023).
    """
    if not image_field:
        return None
    try:
        name = getattr(image_field, 'name', None)
        if not name or str(name).strip() == '':
            return None
        url = image_field.url
        # Normalise http → https for S3 (boto3 can return http in some configs)
        if url and 's3.amazonaws.com' in url and url.startswith('http://'):
            url = 'https://' + url[7:]
        return url
    except ValueError:
        # "has no file associated with it"
        return None
    except Exception as e:
        logger.warning('_safe_url: could not get URL for %r: %s', image_field, e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# HOSPITAL SERIALIZERS
# ──────────────────────────────────────────────────────────────────────────────
class TestRequestSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(), required=False, allow_null=True,
    )
    assigned_to_details = serializers.SerializerMethodField()

    class Meta:
        model = TestRequest
        fields = '__all__'
        read_only_fields = ['requested_by', 'created_at', 'updated_at']
    
    def get_assigned_to_details(self, obj):
        if obj.assigned_to:
            return StaffProfileSerializer(obj.assigned_to).data
        return None
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['assigned_to'] = self.get_assigned_to_details(instance)
        return rep


class VitalRequestSerializer(serializers.ModelSerializer):
    requested_by = ProfileSerializer(read_only=True)
    assigned_to  = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(), required=False, allow_null=True,
    )

    class Meta:
        model  = VitalRequest
        fields = ['id', 'appointment', 'requested_by', 'assigned_to',
                  'note', 'status', 'created_at', 'updated_at']
        read_only_fields = ['requested_by', 'created_at', 'updated_at']


class VitalsSerializer(serializers.ModelSerializer):
    nurse        = ProfileSerializer(read_only=True)
    vital_request = serializers.PrimaryKeyRelatedField(queryset=VitalRequest.objects.all())

    class Meta:
        model  = Vitals
        fields = ['id', 'vital_request', 'nurse', 'blood_pressure',
                  'respiration_rate', 'pulse_rate', 'body_temperature',
                  'height_cm', 'weight_kg', 'recorded_at']
        read_only_fields = ['nurse', 'recorded_at']


class LabResultSerializer(serializers.ModelSerializer):
    lab_scientist = ProfileSerializer(read_only=True)
    test_request  = serializers.PrimaryKeyRelatedField(queryset=TestRequest.objects.all())

    class Meta:
        model  = LabResult
        fields = ['id', 'test_request', 'lab_scientist', 'test_name',
                  'result', 'units', 'reference_range', 'recorded_at']
        read_only_fields = ['lab_scientist', 'recorded_at']


class MedicalReportSerializer(serializers.ModelSerializer):
    doctor = ProfileSerializer(read_only=True)

    class Meta:
        model  = MedicalReport
        fields = ['id', 'appointment', 'doctor', 'medical_condition',
                  'drug_prescription', 'advice', 'next_appointment', 'created_at']
        read_only_fields = ['doctor', 'created_at']


class AssignmentSerializer(serializers.ModelSerializer):
    appointment    = serializers.PrimaryKeyRelatedField(read_only=True)
    appointment_id = serializers.PrimaryKeyRelatedField(
        queryset=Appointment.objects.all(), write_only=True, source='appointment',
    )
    staff    = ProfileSerializer(read_only=True)
    staff_id = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(), write_only=True, source='staff',
    )
    assigned_by = ProfileSerializer(read_only=True)

    class Meta:
        model  = Assignment
        fields = '__all__'
        read_only_fields = ['assigned_by', 'assigned_at']


class AppointmentSerializer(serializers.ModelSerializer):
    patient          = ProfileSerializer(read_only=True)
    doctor           = serializers.PrimaryKeyRelatedField(read_only=True)
    assignments      = AssignmentSerializer(many=True, read_only=True)
    assigned_doctor  = serializers.SerializerMethodField()
    assigned_nurse   = serializers.SerializerMethodField()
    assigned_lab     = serializers.SerializerMethodField()
    test_requests_data = serializers.SerializerMethodField()
    vital_requests_data = serializers.SerializerMethodField()

    class Meta:
        model  = Appointment
        fields = [
            'id', 'patient', 'patient_id', 'name', 'age', 'sex',
            'message', 'address', 'booked_at', 'doctor', 'status',
            'assignments', 'assigned_doctor', 'assigned_nurse', 'assigned_lab',
            'test_requests_data', 'vital_requests_data'
        ]
        read_only_fields = ['booked_at', 'status', 'doctor']

    def get_assigned_doctor(self, obj):
        a = obj.assignments.filter(role='DOCTOR').first()
        return AssignmentSerializer(a).data if a else None

    def get_assigned_nurse(self, obj):
        a = obj.assignments.filter(role='NURSE').first()
        return AssignmentSerializer(a).data if a else None

    def get_assigned_lab(self, obj):
        a = obj.assignments.filter(role='LAB').first()
        return AssignmentSerializer(a).data if a else None
    
    def get_test_requests_data(self, obj):
        requests = obj.test_requests.all()
        return TestRequestSerializer(requests, many=True).data
    
    def get_vital_requests_data(self, obj):
        requests = obj.vital_requests.all()
        return VitalRequestSerializer(requests, many=True).data

    def to_representation(self, instance):
        try:
            cache_key = f"appointment_rep_{instance.id}"
            cached = cache.get(cache_key)
            if cached:
                return cached
            rep = super().to_representation(instance)
        
            rep['test_requests'] = rep.get('test_requests_data', [])
            rep['vital_requests'] = rep.get('vital_requests_data', [])

            try:
                vital_request = instance.vital_requests.last() if hasattr(instance, 'vital_requests') else None
                if vital_request and hasattr(vital_request, 'vitals_entries') and vital_request.vitals_entries.exists():
                    rep['vitals'] = VitalsSerializer(vital_request.vitals_entries.last()).data
            except Exception as e:
                logger.warning(f"Error adding vitals to appointment {instance.id}: {e}")
        
            try:
                lab_results_data = []
                if hasattr(instance, 'test_requests'):
                    for tr in instance.test_requests.all():
                        if tr.lab_results.exists():
                            lab_results_data.extend(
                                LabResultSerializer(tr.lab_results.all(), many=True).data
                                    )
                if lab_results_data:
                    rep['lab_results'] = lab_results_data
            except Exception as e:
                logger.warning(f"Error adding lab results to appointment {instance.id}: {e}") 
            try:
                if hasattr(instance, 'medical_report'):
                    rep['medical_report'] = MedicalReportSerializer(instance.medical_report).data
            except Exception as e:
                logger.warning(f"Error adding medical report to appointment {instance.id}: {e}")
            cache.set(cache_key, rep, 300)
        
            return rep
        except Exception as e:
            logger.error(f"Critical error in to_representation for appointment {instance.id}: {e}")
            return {
                'id': instance.id,
                'name': instance.name,
                'age': instance.age,
                'sex': instance.sex,
                'status': instance.status,
                'booked_at': instance.booked_at,
                'test_requests': [],
                'vital_requests': []
            }


class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient        = ProfileSerializer(read_only=True)
    doctor         = ProfileSerializer(read_only=True)
    assignments    = AssignmentSerializer(many=True, read_only=True)
    test_requests  = TestRequestSerializer(many=True, read_only=True)
    vital_requests = VitalRequestSerializer(many=True, read_only=True)

    class Meta:
        model  = Appointment
        fields = '__all__'


# ──────────────────────────────────────────────────────────────────────────────
# BLOG CATEGORY SERIALIZER
# ──────────────────────────────────────────────────────────────────────────────

class BlogCategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    class Meta:
        model  = BlogCategory
        fields = ['id', 'name', 'slug', 'description', 'post_count']

    def get_post_count(self, obj) -> int:
        """Return published post count for this category."""
        return obj.posts.filter(published=True).count()


# ──────────────────────────────────────────────────────────────────────────────
# BLOG POST SERIALIZERS
# ──────────────────────────────────────────────────────────────────────────────

class SubheadingSerializer(serializers.Serializer):
    id           = serializers.IntegerField(read_only=True)
    title        = serializers.CharField()
    level        = serializers.IntegerField()
    description  = serializers.CharField()
    full_content = serializers.CharField()


class TOCSerializer(serializers.Serializer):
    id     = serializers.IntegerField()
    title  = serializers.CharField()
    level  = serializers.IntegerField()
    anchor = serializers.CharField()


class BlogPostListSerializer(serializers.ModelSerializer):
    subheadings         = serializers.SerializerMethodField()
    featured_image_url  = serializers.SerializerMethodField()
    image_1_url         = serializers.SerializerMethodField()
    image_2_url         = serializers.SerializerMethodField()
    author_name         = serializers.CharField(source='author.fullname', read_only=True)
    author_role         = serializers.CharField(source='author.role',     read_only=True)
    # Nested category object so the frontend has id, name, slug in one payload
    category            = BlogCategorySerializer(read_only=True)
    # Write-only: accept category_id on POST/PATCH without needing a full object
    category_id         = serializers.PrimaryKeyRelatedField(
        queryset=BlogCategory.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = BlogPost
        fields = [
            'id', 'title', 'slug', 'description',
            'featured_image_url', 'image_1_url', 'image_2_url',
            'published', 'created_at', 'table_of_contents',
            'subheadings', 'author_name', 'author_role',
            'category', 'category_id',
        ]

    def get_subheadings(self, obj):
        return [{**s, 'id': i + 1} for i, s in enumerate(obj.subheadings)]

    def get_featured_image_url(self, obj):
        return _safe_url(obj.featured_image)

    def get_image_1_url(self, obj):
        return _safe_url(obj.image_1)

    def get_image_2_url(self, obj):
        return _safe_url(obj.image_2)


class BlogPostSerializer(serializers.ModelSerializer):
    table_of_contents  = TOCSerializer(many=True, read_only=True)
    subheadings        = SubheadingSerializer(many=True, read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    image_1_url        = serializers.SerializerMethodField()
    image_2_url        = serializers.SerializerMethodField()
    author_name        = serializers.CharField(source='author.fullname', read_only=True)
    author_role        = serializers.CharField(source='author.role',     read_only=True)
    category           = BlogCategorySerializer(read_only=True)
    category_id        = serializers.PrimaryKeyRelatedField(
        queryset=BlogCategory.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = BlogPost
        fields = [
            'id', 'title', 'description', 'content',
            'author', 'author_name', 'author_role',
            'featured_image_url', 'image_1_url', 'image_2_url',
            'published', 'published_date', 'created_at', 'updated_at',
            'slug', 'table_of_contents', 'enable_toc', 'subheadings',
            'category', 'category_id',
        ]
        read_only_fields = ['slug', 'table_of_contents', 'subheadings', 'author']

    def get_featured_image_url(self, obj):
        return _safe_url(obj.featured_image)

    def get_image_1_url(self, obj):
        return _safe_url(obj.image_1)

    def get_image_2_url(self, obj):
        return _safe_url(obj.image_2)


class BlogPostCreateSerializer(serializers.ModelSerializer):
    """
    Used for POST (create) and PATCH (update) operations.
    Accepts category_id as a writable integer field so multipart/form-data
    submissions from the BlogEditor can set the category.
    """
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=BlogCategory.objects.all(),
        source='category',
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = BlogPost
        # Exclude the read-only reverse relation so DRF doesn't complain
        exclude = ['category']
        read_only_fields = ['author', 'slug', 'table_of_contents', 'subheadings']

    def to_representation(self, instance):
        """On response, include full category object for convenience."""
        rep = super().to_representation(instance)
        rep['category'] = BlogCategorySerializer(instance.category).data if instance.category else None
        return rep


# ──────────────────────────────────────────────────────────────────────────────
# BLOG SEARCH SUGGESTION SERIALIZER
# ──────────────────────────────────────────────────────────────────────────────

class BlogPostSuggestionSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for search autocomplete suggestions.
    Returns only what the dropdown needs: id, title, slug, category name.
    """
    category_name = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()

    class Meta:
        model  = BlogPost
        fields = ['id', 'title', 'slug', 'category_name', 'category_slug']

    def get_category_name(self, obj) -> str:
        return obj.category.name if obj.category else 'General Health'

    def get_category_slug(self, obj) -> str:
        return obj.category.slug if obj.category else ''


# ──────────────────────────────────────────────────────────────────────────────
# STAFF / PROFILE SERIALIZERS
# ──────────────────────────────────────────────────────────────────────────────

class StaffProfileSerializer(serializers.ModelSerializer):
    user        = serializers.StringRelatedField(read_only=True)
    profile_pix = serializers.SerializerMethodField()

    class Meta:
        model  = Profile
        fields = ['id', 'user', 'fullname', 'phone', 'gender', 'profile_pix', 'role']

    def get_profile_pix(self, obj):
        return _safe_url(obj.profile_pix)


class AppointmentAssignmentSerializer(serializers.Serializer):
    appointment_id = serializers.IntegerField(required=True)
    staff_id       = serializers.IntegerField(required=True)
    role           = serializers.ChoiceField(choices=['DOCTOR', 'NURSE', 'LAB'], required=True)
    notes          = serializers.CharField(required=False, allow_blank=True)