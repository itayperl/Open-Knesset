from django.db import models
from knesset.mks.models import Member, Party
from tagging.models import Tag, TaggedItem
from knesset.tagvotes.models import TagVote

from tagging.forms import TagField
from django import forms
from django.utils.translation import ugettext_lazy as _

VOTE_ACTION_TYPE_CHOICES = (
        (u'for', u'For'),
        (u'against', u'Against'),
        (u'abstain', u'Abstain'),
        (u'no-vote', u'No Vote'),
)


class PartyVotingStatistics(models.Model):
    party = models.OneToOneField('mks.Party',related_name='voting_statistics')
    
    def votes_against_party_count(self):
        return VoteAction.objects.filter(member__current_party=self.party, against_party=True).count()

    def votes_count(self):
        return VoteAction.objects.filter(member__current_party=self.party).count()

    def discipline(self):
        total_votes = self.votes_count()
        votes_against_party = self.votes_against_party_count()
        return round(100.0*(total_votes-votes_against_party)/total_votes,1)
        
    
    def __unicode__(self):
        return "%s" % self.party.name


class MemberVotingStatistics(models.Model):
    member = models.OneToOneField('mks.Member', related_name='voting_statistics')



class VoteAction(models.Model):
    type   = models.CharField(max_length=10,choices=VOTE_ACTION_TYPE_CHOICES)
    member = models.ForeignKey('mks.Member')
    vote   = models.ForeignKey('Vote')
    against_party = models.BooleanField(default=False)
    against_coalition = models.BooleanField(default=False)
    against_opposition = models.BooleanField(default=False)
    def __unicode__(self):
        return "%s %s %s" % (self.member.name, self.type, self.vote.title)
 

class Vote(models.Model):
    meeting_number = models.IntegerField(null=True,blank=True)
    vote_number    = models.IntegerField(null=True,blank=True)    
    src_id         = models.IntegerField(null=True,blank=True)    
    src_url  = models.URLField(verify_exists=False, max_length=1024,null=True,blank=True)
    title          = models.CharField(max_length=1000)
    time           = models.DateTimeField()
    time_string    = models.CharField(max_length=100)
    votes          = models.ManyToManyField('mks.Member', related_name='votes', blank=True, through='VoteAction')
    importance     = models.FloatField()
    summary        = models.TextField(null=True,blank=True)    
    full_text      = models.TextField(null=True,blank=True)
    full_text_url  = models.URLField(verify_exists=False, max_length=1024,null=True,blank=True)

    class Meta:
        ordering = ('-time',)
        verbose_name = _('Vote')
        verbose_name_plural = _('Votes')

    def __unicode__(self):
        return "%s (%s)" % (self.title, self.time_string)

    def get_voters_id(self, vote_type):
        return VoteAction.objects.filter(vote=self, type=vote_type).values_list('member__id', flat=True)

    def for_votes_count(self):
        return self.votes.filter(voteaction__type='for').count()

    def for_votes(self):
        #return self.votes.filter(voteaction__type='for')
        return VoteAction.objects.filter(vote=self, type='for')

    def against_votes_count(self):
        return self.votes.filter(voteaction__type='against').count()

    def against_votes(self):
        #return self.votes.filter(voteaction__type='against')
        return VoteAction.objects.filter(vote=self, type='against')

    def against_party_votes_count(self):
        return VoteAction.objects.filter(vote=self, against_party=True).count()

    def against_coalition_votes_count(self):
        return VoteAction.objects.filter(vote=self, against_coalition=True).count()

    def against_opposition_votes_count(self):
        return VoteAction.objects.filter(vote=self, against_opposition=True).count()


    def short_summary(self):
        if self.summary==None:
            return ''
        else:
            return self.summary[:60]

    def full_text_link(self):
        if self.full_text_url==None:
            return ''
        else:
            return '<a href="%s">link</a>' % self.full_text_url
    full_text_link.allow_tags = True  

    @models.permalink
    def get_absolute_url(self):
        return ('vote-detail', [str(self.id)])

    def _get_tags(self):
        tags = Tag.objects.get_for_object(self)
        for t in tags:
            ti = TaggedItem.objects.filter(tag=t).filter(object_id=self.id)[0]
            t.score = sum(TagVote.objects.filter(tagged_item=ti).values_list('vote',flat=True))
            t.score_positive = t.score > 0
        tags = [t for t in tags]        
        tags.sort(key=lambda x:-x.score)
        return tags

    def _set_tags(self, tag_list):
        Tag.objects.update_tags(self, tag_list)

    tags = property(_get_tags, _set_tags)

    def tags_with_user_votes(self, user):
        tags = Tag.objects.get_for_object(self)
        for t in tags:
            ti = TaggedItem.objects.filter(tag=t).filter(object_id=self.id)[0]
            t.score = sum(TagVote.objects.filter(tagged_item=ti).values_list('vote',flat=True))
            v = TagVote.objects.filter(tagged_item=ti).filter(user=user)
            if(len(v)>0):
                t.user_score = v[0].vote
            else:
                t.user_score = 0
        return tags.sorted(cmp=lambda x,y:cmp(x.score, y.score))



    def tag_form(self):
        tf = TagForm()
        tf.tags = self.tags
        tf.initial = {'tags':', '.join([str(t) for t in self.tags])}
        return tf

class TagForm(forms.Form):
    tags = TagField()