# hospital/management/commands/seed_blog_posts.py
from django.core.management.base import BaseCommand
from hospital.models import BlogPost
from users.models import Profile
from django.utils import timezone
import boto3
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seed blog posts with existing S3 images'

    def handle(self, *args, **kwargs):
        # Check if blog posts already exist
        if BlogPost.objects.filter(published=True).exists():
            self.stdout.write(self.style.WARNING('Blog posts already exist. Skipping seed.'))
            return

        # Get or create an admin
        admin = Profile.objects.filter(role='ADMIN').first()
        if not admin:
            admin = Profile.objects.first()
            if admin:
                admin.role = 'ADMIN'
                admin.save()
                self.stdout.write(f'Made {admin.fullname} an admin')
        
        if not admin:
            self.stdout.write(self.style.ERROR('No profiles found! Please register a user first.'))
            return

        self.stdout.write(f'Using admin: {admin.fullname}')

        # Blog posts data
        blog_posts_data = [
            {
                "title": "The Importance of Regular Exercise",
                "description": "Regular physical activity is essential for maintaining good health and preventing chronic diseases.",
                "content": "<h2>Why Exercise Matters</h2><p>Exercise helps control weight, combats health conditions, and improves mood.</p><h2>Types of Exercise</h2><p>Include cardio, strength training, and flexibility exercises in your routine.</p>",
                "featured_image": "blog_images/Exercise-Right-Blog-Images-7-1536x1044.png",
                "image_1": "blog_images/exercise2.jpg",
                "image_2": "blog_images/exercise3.jpg",
            },
            {
                "title": "Understanding Prostate Cancer",
                "description": "Learn about prostate cancer symptoms, diagnosis, and treatment options.",
                "content": "<h2>What is Prostate Cancer?</h2><p>Prostate cancer occurs in the prostate gland and is one of the most common types of cancer in men.</p><h2>Symptoms</h2><p>Common symptoms include difficulty urinating and blood in urine.</p>",
                "featured_image": "blog_images/prostatecancer1.jpg",
                "image_1": "blog_images/prostatecancer2.jpg",
                "image_2": "blog_images/prostate-cancer3.webp",
            },
            {
                "title": "Healthy Eating Habits for Better Living",
                "description": "Discover how proper nutrition can improve your overall health and wellbeing.",
                "content": "<h2>Balanced Diet</h2><p>A balanced diet includes fruits, vegetables, whole grains, and lean proteins.</p><h2>Hydration</h2><p>Drink plenty of water throughout the day.</p>",
                "featured_image": "blog_images/ginger1.jpg",
                "image_1": "blog_images/ginger2.png",
                "image_2": "blog_images/ginger3.jpg",
            },
            {
                "title": "Benefits of Regular Health Checkups",
                "description": "Why routine medical checkups are crucial for maintaining optimal health.",
                "content": "<h2>Prevention is Better Than Cure</h2><p>Regular checkups help detect health issues early when they're more treatable.</p>",
                "featured_image": "blog_images/orange1.jpg",
                "image_1": "blog_images/orange2.jpeg",
                "image_2": "blog_images/orange3.webp",
            },
        ]

        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        created_count = 0
        for post_data in blog_posts_data:
            # Verify images exist in S3
            missing_images = []
            for img_field in ['featured_image', 'image_1', 'image_2']:
                if img_field in post_data:
                    s3_key = f"media/{post_data[img_field]}"
                    try:
                        s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
                    except:
                        missing_images.append(post_data[img_field])
            
            if missing_images:
                self.stdout.write(self.style.WARNING(
                    f'Skipping "{post_data["title"]}" - missing images: {missing_images}'
                ))
                continue

            # Create blog post
            post = BlogPost.objects.create(
                title=post_data['title'],
                description=post_data['description'],
                content=post_data['content'],
                author=admin,
                published=True,
                published_date=timezone.now(),
                enable_toc=True,
                featured_image=post_data.get('featured_image'),
                image_1=post_data.get('image_1'),
                image_2=post_data.get('image_2'),
            )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(
                f'Created: {post.title} (Featured: {post.featured_image.name})'
            ))

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {created_count} blog posts!'))