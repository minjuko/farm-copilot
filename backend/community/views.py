from common.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import DatabaseError, IntegrityError
from django.db.models import Count
from .models import Post, Comment
from .forms import PostForm, CommentForm
from common.exceptions import ValidationError, NotFoundError, InternalServerError, InvalidRequestError, DuplicateResourceError
import logging
import json

logger = logging.getLogger(__name__)

def post_list(request):
    if request.method != 'GET':
        raise InvalidRequestError("GET method only allowed")
    try:
        post_type = request.GET.get('post_type')
        valid_post_types = {choice for choice, _ in PostForm.POST_TYPE_CHOICES}
        if post_type and post_type not in valid_post_types:
            raise ValidationError("Invalid post type")
        if post_type:
            posts = Post.objects.filter(post_type=post_type).annotate(comment_count=Count('comments')).order_by('-creation_date', '-id').values('id', 'title', 'content', 'user__username', 'creation_date', 'comment_count')
        else:
            posts = Post.objects.annotate(comment_count=Count('comments')).order_by('-creation_date', '-id').values('id', 'title', 'content', 'user__username', 'creation_date', 'comment_count')
        return JsonResponse(list(posts), safe=False)
    except ValidationError:
        raise
    except DatabaseError as e:
        logger.error(f"Database error while fetching posts: {str(e)}")
        raise InternalServerError("Database error occurred while fetching posts.")

def post_detail(request, post_id):
    if request.method != 'GET':
        raise InvalidRequestError("GET method only allowed")
    try:
        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist as exc:
            raise NotFoundError("Post not found") from exc
        comments = list(post.comments.order_by('created_at', 'id').values(
            'id', 'content', 'user__username', 'user_id', 'created_at', 'parent_id'
        ))

        # Ensure the image URL is correctly handled
        if post.image and hasattr(post.image, 'url'):
            image_url = post.image.url
        else:
            image_url = None

        post_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'post_type': post.post_type,
            'user_id': post.user.id,
            'username': post.user.username,
            'creation_date': post.creation_date,
            'image': image_url,
            'comments': comments,
        }
        return JsonResponse(post_data)
    except NotFoundError:
        raise
    except DatabaseError as e:
        logger.error(f"Database error on retrieving post details: {str(e)}")
        return JsonResponse({'error': 'Database error occurred while retrieving post details.'}, status=500)
    except Exception as e:
        logger.error(f"Unhandled exception on retrieving post details: {str(e)}")
        return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)



@login_required
def post_create(request):
    if request.method != 'POST':
        raise InvalidRequestError("POST method only allowed")
    try:
        form = PostForm(request.POST, request.FILES)
        if not form.is_valid():
            raise ValidationError("Form validation failed")
        post = form.save(commit=False)
        post.user = request.user
        post.post_type = request.POST.get('post_type')
        post.save()
        return JsonResponse({'id': post.pk, 'status': 'success'}, status=201)
    except ValidationError:
        raise
    except IntegrityError as e:
        logger.error(f"Integrity error on creating post: {str(e)}")
        raise DuplicateResourceError("Duplicate post cannot be created.")
    except DatabaseError as e:
        logger.error(f"Database error on creating post: {str(e)}")
        raise InternalServerError("Database error occurred while creating post.")
    except Exception as e:
        logger.error(f"Unhandled exception in post creation: {str(e)}")
        raise InternalServerError("An unexpected error occurred while creating the post.")
    
@login_required
def post_edit(request, post_id):
    if request.method != 'POST':
        raise InvalidRequestError("POST method only allowed")
    try:
        try:
            post = Post.objects.get(pk=post_id, user=request.user)
        except Post.DoesNotExist as exc:
            raise NotFoundError("Post not found") from exc
        form = PostForm(request.POST, request.FILES, instance=post)
        if not form.is_valid():
            raise ValidationError("Form validation failed")
        form.save()
        return JsonResponse({'status': 'success'}, status=200)
    except (NotFoundError, ValidationError):
        raise
    except IntegrityError as e:
        logger.error(f"Integrity error on editing post: {str(e)}")
        raise ValidationError("Duplicate data provided.")
    except Exception as e:
        logger.error(f"Error editing post: {str(e)}")
        raise InternalServerError("Failed to edit post")

@login_required
def post_delete(request, post_id):
    try:
        if request.method != 'POST':
            raise InvalidRequestError("GET method not allowed.")
        try:
            post = Post.objects.get(pk=post_id, user=request.user)
        except Post.DoesNotExist as exc:
            raise NotFoundError("Post not found.") from exc
        post.delete()
        return HttpResponse(status=204)
    except (InvalidRequestError, NotFoundError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise InternalServerError("An unexpected error occurred.")

@login_required
def comment_create(request, post_id):
    if request.method != 'POST':
        raise InvalidRequestError("POST method only allowed")
    try:
        data = json.loads(request.body)
        form = CommentForm(data)
        if not form.is_valid():
            raise ValidationError("Form validation failed")
        comment = form.save(commit=False)
        comment.user = request.user
        try:
            comment.post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist as exc:
            raise NotFoundError("Post related to the comment not found") from exc

        parent_id = data.get('parent_id')
        if parent_id not in (None, ''):
            try:
                parent = Comment.objects.get(pk=parent_id, post=comment.post)
            except (Comment.DoesNotExist, ValueError, TypeError) as exc:
                raise ValidationError("Parent comment must belong to this post") from exc
            comment.parent = parent
        comment.save()
        return JsonResponse({
            'id': comment.id,
            'content': comment.content,
            'user_id': comment.user.id,
            'user__username': comment.user.username,
            'created_at': comment.created_at,
            'parent_id': comment.parent_id
        }, status=201)
    except (ValidationError, NotFoundError):
        raise
    except IntegrityError as e:
        logger.error(f"Integrity error on creating comment: {str(e)}")
        raise DuplicateResourceError("Duplicate comment cannot be created.")
    except DatabaseError as e:
        logger.error(f"Database error on creating comment: {str(e)}")
        raise InternalServerError("Database error occurred while creating comment.")
    except json.JSONDecodeError:
        raise ValidationError("Invalid JSON format")
    except Exception as e:
        logger.error(f"Unhandled exception in comment creation: {str(e)}")
        raise InternalServerError("An unexpected error occurred while creating the comment")

@login_required
def comment_edit(request, comment_id):
    if request.method != 'POST':
        raise InvalidRequestError("POST method only allowed")
    try:
        try:
            comment = Comment.objects.get(pk=comment_id, user=request.user)
        except Comment.DoesNotExist as exc:
            raise NotFoundError("Comment not found") from exc
        data = json.loads(request.body)
        form = CommentForm(data, instance=comment)
        if not form.is_valid():
            raise ValidationError("Form validation failed")
        form.save()
        return JsonResponse({
            'id': comment.id,
            'content': comment.content,
            'user_id': comment.user.id,
            'created_at': comment.created_at
        }, status=200)
    except (NotFoundError, ValidationError):
        raise
    except json.JSONDecodeError:
        raise ValidationError("Invalid JSON format")
    except IntegrityError as e:
        logger.error(f"Integrity error on editing comment: {str(e)}")
        raise ValidationError("Duplicate data provided.")
    except Exception as e:
        logger.error(f"Error editing comment: {str(e)}")
        raise InternalServerError("Failed to edit comment")

@login_required
def comment_delete(request, comment_id):
    if request.method != 'POST':
        raise InvalidRequestError("POST method only allowed")
    try:
        try:
            comment = Comment.objects.get(pk=comment_id, user=request.user)
        except Comment.DoesNotExist as exc:
            raise NotFoundError("Comment not found") from exc
        comment.delete()
        return HttpResponse(status=204)
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        raise InternalServerError("Failed to delete comment")

@login_required
def my_post_list(request):
    if request.method != 'GET':
        raise InvalidRequestError("GET method only allowed")
    try:
        posts = Post.objects.filter(user=request.user).order_by('-creation_date', '-id').values('id', 'title', 'content', 'user__username', 'creation_date')
        return JsonResponse(list(posts), safe=False)
    except DatabaseError as e:
        logger.error(f"Database error fetching user's posts: {str(e)}")
        raise InternalServerError("Database error occurred while fetching user's posts")

@login_required
def my_commented_posts(request):
    if request.method != 'GET':
        raise InvalidRequestError("GET method only allowed")
    try:
        comments = Comment.objects.filter(user=request.user).values('post').distinct()
        post_ids = [comment['post'] for comment in comments]
        posts = Post.objects.filter(id__in=post_ids).order_by('-creation_date', '-id').values('id', 'title', 'content', 'user__username', 'creation_date')
        return JsonResponse(list(posts), safe=False)
    except DatabaseError as e:
        logger.error(f"Database error fetching commented posts: {str(e)}")
        raise InternalServerError("Database error occurred while fetching posts commented by user")
