from django.db import models
from django.conf import settings
from django.utils import timezone
from aivle_big.storage_backends import PestDetectionStorage

class Pest(models.Model):
    """
    Model to store information about different types of pests.
    """
    pest_name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    occurrence_environment = models.TextField(blank=True, null=True)
    symptom_description = models.TextField(blank=True, null=True)
    prevention_methods = models.TextField(blank=True, null=True)
    pesticide_name = models.CharField(max_length=100, blank=True, null=True)
    image_url = models.URLField(max_length=200, blank=True, null=True)  # URL to an informational image
    information_source = models.CharField(max_length=100, blank=True, null=True)
    information_source_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.pest_name


class PestModelClass(models.Model):
    """Explicit contract between a model class index and a Pest record."""

    class_id = models.PositiveIntegerField(unique=True)
    model_label = models.CharField(max_length=100)
    pest = models.ForeignKey(
        Pest,
        on_delete=models.CASCADE,
        related_name='model_classes',
    )

    class Meta:
        db_table = 'pest_model_class'
        ordering = ['class_id']

    def __str__(self):
        return f'{self.class_id}: {self.model_label}'

class PestDetection(models.Model):
    """
    Model to store instances of pest detections, linking to the Pest model.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pest_detections'
    )
    pest = models.ForeignKey(
        Pest,
        on_delete=models.CASCADE,
        related_name='detections'
    )
    image = models.ImageField(
        upload_to='pest_detections/', 
        storage=PestDetectionStorage(),  # Using custom storage backend
        blank=True, 
        null=True
    )
    detection_date = models.DateTimeField(default=timezone.now)
    confidence = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.pest.pest_name} detected by {self.user.username} on {self.detection_date.strftime('%Y-%m-%d %H:%M')} with {self.confidence}% confidence"
