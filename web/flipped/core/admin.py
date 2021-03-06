import json

import itertools
from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

import core.models
from core.utils import get_jstree_data
from reverseadmin import ReverseModelAdmin


class VideoPageAdmin(admin.ModelAdmin):
    list_display = ('id', 'video_title', 'youtube_movie_id')


class TeachItemAdmin(admin.ModelAdmin):
    exclude = ('video_count_cache',)


class TeachTopicAdmin(admin.ModelAdmin):
    exclude = ('video_count_cache',)


class SubtitlesListFilter(admin.SimpleListFilter):
    title = _('subtitles')
    parameter_name = 'sub'

    def lookups(self, request, model_admin):
        return ('hebrew', 'Hebrew'),

    def queryset(self, request, queryset):
        if self.value() == 'hebrew':
            return queryset.filter(video_subtitles__in=['he', 'iw'])
        return queryset


class VideoDurationListFilter(admin.SimpleListFilter):
    title = _('video duration')
    parameter_name = 'duration'

    def lookups(self, request, model_admin):
        return (1, '0-10 min'), (2, '10-20 min'), (3, '20+ min')

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(
                Q(video_duration__regex=r'^PT[0-9]M[0-9]{0,2}S?$') | Q(video_duration__regex=r'^PT[0-9]{1,2}S$'))
        elif self.value() == '2':
            return queryset.filter(video_duration__regex=r'^PT1[0-9]M[0-9]{0,2}S?$')
        elif self.value() == '3':
            return queryset.filter(Q(video_duration__regex=r'^PT[2-9][0-9]M[0-9]{0,2}S?$') |
                                   Q(video_duration__regex=r'^PT[0-9]{3,}M[0-9]{0,2}S?$'))
        return queryset


class CandidateVideoPageAdmin(ReverseModelAdmin):
    list_display = (
        'video_title', 'state', 'video_duration', 'related_teach_item', 'hebrew', 'hebrew_subtitles', 'vote_views', 'playing_views', 'up_votes',
        'down_votes', 'youtube_channel')
    list_select_related = ('related_video_page', 'related_video_page__teach_item')
    list_filter = ('state', VideoDurationListFilter, SubtitlesListFilter, 'related_video_page__teach_item')

    inline_type = 'stacked'
    inline_reverse = (
        ('video_page', {'fields': ('category', 'teach_item', 'video_title', 'user')}),
    )

    readonly_fields = (
        'youtube_movie_id_html', 'youtube_channel', 'video_title', 'video_description', 'video_upload_date',
        'video_duration', 'video_subtitles', 'candidate_reason', 'related_video_page', 'video_page')

    exclude = ['youtube_movie_id']
    actions = ['mark_irrelevant']

    def related_teach_item(self, obj):
        return obj.related_video_page.teach_item.title

    related_teach_item.admin_order_field = 'related_video_page__teach_item__title'

    def mark_irrelevant(self, request, queryset):
        queryset.exclude(state=core.models.CandidateVideoPage.STATE_PROMOTED).update(state=core.models.CandidateVideoPage.STATE_IRRELEVANT)

    mark_irrelevant.short_description = "Mark selected candidates as irrelevant"

    def youtube_movie_id_html(self, instance):
        return format_html('<a href=https://www.youtube.com/watch?v={} target="_blank">{}</a>',
                           instance.youtube_movie_id, instance.youtube_movie_id)

    youtube_movie_id_html.short_description = 'Youtube movie id'

    def save_related(self, request, form, formsets, change):
        del formsets[0]
        super(CandidateVideoPageAdmin, self).save_related(request, form, formsets, change)

    def response_change(self, request, obj):
        if obj.state != core.models.CandidateVideoPage.STATE_PROMOTED and "_promote" in request.POST:
            if not obj.video_page:
                obj.video_page = core.models.VideoPage(user=request.user, teach_item=obj.related_video_page.teach_item)

            obj.video_page.category = request.POST['form-0-category']
            obj.video_page.teach_item_id = request.POST['form-0-teach_item']
            obj.video_page.video_title = request.POST['form-0-video_title']

            obj.video_page.youtube_movie_id = obj.youtube_movie_id
            obj.video_page.youtube_channel = obj.youtube_channel
            obj.video_page.youtube_channel_id = obj.youtube_channel_id
            obj.video_page.video_description = obj.video_description
            obj.video_page.video_upload_date = obj.video_upload_date
            obj.video_page.video_duration = obj.video_duration
            obj.video_page.save()

            obj.video_page_id = obj.video_page.id
            obj.state = core.models.CandidateVideoPage.STATE_PROMOTED

        if obj.state != core.models.CandidateVideoPage.STATE_PROMOTED and obj.video_page:
            obj.video_page.delete()
            obj.video_page = None

        obj.save()

        return super(CandidateVideoPageAdmin, self).response_change(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        root_topics = list(core.models.TeachTopic.objects.root_topics(for_teacher=False))
        root_subtree = list(itertools.chain.from_iterable(map(lambda topic: topic.get_subtree(), root_topics)))
        root_topics.extend(root_subtree)
        extra_context['jstree_data'] = json.dumps(get_jstree_data(root_topics, None, opened=False, enable_items_only=True,
                                                                  include_video_count=False))
        return super(CandidateVideoPageAdmin, self).change_view(request, object_id, form_url, extra_context=extra_context)


admin.site.register(core.models.CandidateVideoPage, admin_class=CandidateVideoPageAdmin)
admin.site.register(core.models.VideoPage, admin_class=VideoPageAdmin)
admin.site.register(core.models.TextualReview)
admin.site.register(core.models.RatingReview)
admin.site.register(core.models.TeachItem, admin_class=TeachItemAdmin)
admin.site.register(core.models.TeachTopic, admin_class=TeachTopicAdmin)
admin.site.register(core.models.TopicSuggestion)
