# Create your models here.
from re import finditer
from decimal import Decimal

from django.db import models
from infty.users.models import User
from django.contrib.postgres.fields import JSONField

from django.db.models import Sum

class GenericModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Thing(GenericModel):
    """
    F: Things are references to anything with respect to which we
    will formulate goals. To be implemented in blockchain db.
    """
    ASSET = 0
    AGENT = 1
    PLACE = 2
    EVENT = 3
    TOPIC = 4

    THING_TYPES = [
        (ASSET, 'Asset'),
        (AGENT, 'Agent'),
        (PLACE, 'Place'),
        (EVENT, 'Event'),
        (TOPIC, 'Topic'),
    ]

    type = models.PositiveSmallIntegerField(THING_TYPES, default=TOPIC)


class Topic(GenericModel):
    """
    Y: Main content type, to include fields of all infty types.

    Note: 'STEP' is missing intentionally. 'TASK' and 'STEP' are
    redundant, and in the choice, which one to get rid of, 'STEP'
    made more sense to remove, because people have theories of HTN
    (hierarchical task networks), and 'TASK' is understood as 'STEP'
    by AI planning community. Also 'TASK' is much more tangible thing
    to start with for people. We'll introduce the fields of 'STEP'
    (e.g., planning I/O, https://github.com/wefindx/StepIO) later.
    """
    NEED = 0 # Goal condition
    GOAL = 1
    IDEA = 2
    PLAN = 3
    TASK = 4

    TOPIC_TYPES = [
        (NEED, 'Need'),
        (GOAL, 'Goal'),
        (IDEA, 'Idea'),
        (PLAN, 'Plan'),
        (TASK, 'Task'),
    ]

    type = models.PositiveSmallIntegerField(TOPIC_TYPES, default=TASK)
    title = models.TextField()
    body = models.TextField(null=True, blank=True)

    owner = models.ForeignKey(User)
    editors = models.ManyToManyField(
        User,
        related_name='topic_editors',
        blank=True
    )
    parents = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='parent_topics'
    )

    def __str__(self):
        return self.title


class Comment(GenericModel):
    """
    X: Comments are the place to discuss and claim time and things.

    Note: the reason why we need a separate model for Comment,
    is because comments should not have multiple editors.
    """

    topic = models.ForeignKey(Topic)
    text = models.TextField()

    claimed_hours = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)
    assumed_hours = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)

    owner = models.ForeignKey(User)

    def save(self, *args, **kwargs):
        """
        Save comment created date to parent object.
        """

        if self.pk:
            """
            We create new snapshot, if changed.
            We determine the difference between new and snapshot.
            And create new ContributionCertificates if needed.
            """

            # Interaction(self, obj)

            obj = Comment.objects.get(pk=self.pk)
            old = self.parse_hours(obj.text)
            new = self.parse_hours(self.text)


            # Monotonicity
            # 1. new (.claimed_hours+.assumed_hours) >= comment.invested()
            if (new['claimed_hours'] + new['assumed_hours']) < obj.invested():
                """
                Cannot remove time already paid for, don't .save().
                """
                pass
            # 2. new (.claimed_hours) >=  previously .matched_time.
            elif new['claimed_hours'] < obj.matched():
                """
                Cannot remove time matched, don't .save().
                """
                pass
            else:
            # Else, it is okay to proceed.

                # Subjects:
                AMOUNT = new['claimed_hours'] - obj.matched()

                # Taking snapshot
                snapshot = self.create_snapshot()

                # Recording interaction
                ix = Interaction(
                    comment=self,
                    snapshot=snapshot,
                    claimed_hours_to_match=AMOUNT,
                )
                ix.save()

                """ Going in pairs over all unmatched, unbroken certificates
                ContributionCertificates of the comment, and creating matched and unmatched children certificates.
                """

                DOER = 0
                INVESTOR = 1

                cert1 = None
                for i, cert2 in enumerate(
                        ContributionCertificate.objects.filter(
                            transaction__comment=self,
                            broken=False,
                            matched=False,
                        ).order_by('pk').all()):
                    if i % 2 == 0:
                        cert1 = cert2
                        continue
                    """ Iterating over certificate pairs. """

                    # PAIR INTEGRITY CHECKS - PAIR MUST BE SYMMETRIC:
                    if not ((cert1.transaction == cert2.transaction) & \
                       (cert1.type == DOER) & \
                       (cert2.type == INVESTOR) & \
                       (cert1.hours == cert2.hours)):
                        " Don't proceed if these conditions not satisfied. "
                        break

                    certs_hours = cert1.hours + cert2.hours


                    if AMOUNT >= certs_hours:

                        " Create matched certs. (2) "

                        doer_cert = ContributionCertificate(
                            type=DOER,
                            transaction=cert1.transaction,
                            interaction=ix,
                            comment_snapshot=cert1.comment_snapshot,
                            hours=cert1.hours,
                            matched=True,
                            received_by=cert1.received_by,
                            broken=False,
                            parent=cert1,
                        )
                        doer_cert.save()
                        investor_cert = ContributionCertificate(
                            type=INVESTOR,
                            transaction=cert2.transaction,
                            interaction=ix,
                            comment_snapshot=cert2.comment_snapshot,
                            hours=cert2.hours,
                            matched=True,
                            received_by=cert2.received_by,
                            broken=False,
                            parent=cert2,
                        )
                        investor_cert.save()

                        " Mark original cert as broken "

                        cert1.broken = True; cert1.save()
                        cert2.broken = True; cert2.save()

                        " reduce number of hours covered "
                        AMOUNT -= certs_hours

                    elif AMOUNT < certs_hours:
                        " Create matched and unmatched certs. (4) "

                        hours_to_match = AMOUNT/Decimal(2)

                        doer_cert = ContributionCertificate(
                            type=DOER,
                            transaction=cert1.transaction,
                            interaction=ix,
                            comment_snapshot=cert1.comment_snapshot,
                            hours=hours_to_match,
                            matched=True,
                            received_by=cert1.received_by,
                            broken=False,
                            parent=cert1,
                        )
                        doer_cert.save()
                        investor_cert = ContributionCertificate(
                            type=INVESTOR,
                            transaction=cert2.transaction,
                            interaction=ix,
                            comment_snapshot=cert2.comment_snapshot,
                            hours=hours_to_match,
                            matched=True,
                            received_by=cert2.received_by,
                            broken=False,
                            parent=cert2,
                        )
                        investor_cert.save()

                        hours_to_donate = (certs_hours-AMOUNT)/Decimal(2)

                        doer_cert = ContributionCertificate(
                            type=DOER,
                            transaction=cert1.transaction,
                            interaction=ix,
                            comment_snapshot=cert1.comment_snapshot,
                            hours=hours_to_donate,
                            matched=False,
                            received_by=cert1.received_by,
                            broken=False,
                            parent=cert1,
                        )
                        doer_cert.save()
                        investor_cert = ContributionCertificate(
                            type=INVESTOR,
                            transaction=cert2.transaction,
                            interaction=ix,
                            comment_snapshot=cert2.comment_snapshot,
                            hours=hours_to_donate,
                            matched=False,
                            received_by=cert2.received_by,
                            broken=False,
                            parent=cert2,
                        )
                        investor_cert.save()

                        " Mark original cert as broken "

                        cert1.broken = True; cert1.save()
                        cert2.broken = True; cert2.save()

                        " reduce number of hours covered "
                        # AMOUNT = Decimal(0.0)
                        AMOUNT -= hours_to_donate

                        " Break the iteration "
                        break

                self.set_hours()
                super(Comment, self).save(*args, **kwargs)

        else:
            self.set_hours()
            super(Comment, self).save(*args, **kwargs)

    def set_hours(self):

        parsed = self.parse_hours(self.text)

        self.claimed_hours = parsed['claimed_hours']
        self.assumed_hours = parsed['assumed_hours']

    def parse_hours(self, text):
        """
        Given text, e.g., comment text, parses the
        claimed_hours and assumed_hours.
        """

        claimed_hours = Decimal(0.0)
        assumed_hours = Decimal(0.0)

        for m in finditer('\{([^}]+)\}', text):
            token = m.group(1)
            if token:
                if token[0] == '?':
                    try:
                        hours = float(token[1:])
                        assumed_hours += Decimal(hours)
                    except:
                        pass
                else:
                    try:
                        hours = float(token)
                        claimed_hours += Decimal(hours)
                    except:
                        pass
        return {
            'claimed_hours': claimed_hours,
            'assumed_hours': assumed_hours,
        }

    def create_snapshot(self):

        snapshot = CommentSnapshot(
            comment=self,
            text=self.text,
            claimed_hours=self.claimed_hours,
            assumed_hours=self.assumed_hours,
            owner=self.owner
        )

        snapshot.save()

        return snapshot

    def contributions(self):
        return ContributionCertificate.objects.filter(
                comment_snapshot__comment=self).count()

    def matched(self, by=None):
        """
        Hours matched.
        """
        if by:
            return Decimal(ContributionCertificate.objects.filter(
                comment_snapshot__comment=self, matched=True, broken=False, received_by=by).aggregate(
                total=Sum('hours')
            ).get('total') or 0)

        return Decimal(ContributionCertificate.objects.filter(
            comment_snapshot__comment=self, matched=True, broken=False).aggregate(
            total=Sum('hours')
        ).get('total') or 0)

    def donated(self, by=None):
        """
        Hours donated.
        """
        if by:
            return Decimal(ContributionCertificate.objects.filter(
                comment_snapshot__comment=self, matched=False, broken=False, received_by=by).aggregate(
                total=Sum('hours')
            ).get('total') or 0)


        return Decimal(ContributionCertificate.objects.filter(
            comment_snapshot__comment=self, matched=False, broken=False).aggregate(
            total=Sum('hours')
        ).get('total') or 0)

    def invested(self):
        """
        Hours invested.  = self.matched() + self.donated()
        """

        return Decimal(ContributionCertificate.objects.filter(
            comment_snapshot__comment=self, broken=False).aggregate(
            total=Sum('hours')
        ).get('total') or 0)

    def remains(self):
        """
        Hours in comment, not yet covered by investment.
        """
        return self.claimed_hours + self.assumed_hours - self.invested()

    def invest(self, hour_amount, payment_currency_label, investor):
        """
        Investing into .claimed_time, and .assumed_time.
        Generating Transaction, ContributionCertificates for
        comment owner, and investor.
        """

        AMOUNT = min(Decimal(hour_amount), self.remains())

        CURRENCY = Currency.objects.get(
            label=payment_currency_label.upper()
        )

        VALUE = CURRENCY.in_hours(objects=True)

        if AMOUNT:

            amount = AMOUNT / VALUE['in_hours']

            snapshot = self.create_snapshot()

            tx = Transaction(
                comment=self,
                snapshot=snapshot,
                hour_price=VALUE['hour_price_snapshot'],
                currency_price=VALUE['currency_price_snapshot'],

                payment_amount=amount,
                payment_currency=CURRENCY,
                payment_recipient=self.owner,
                payment_sender=investor,
                hour_unit_cost=Decimal(1.)/VALUE['in_hours'],
            )
            tx.save()

            return tx

    def __str__(self):
        return "Comment for {}".format(self.topic)


class CommentSnapshot(GenericModel):
    """
    Whenever comment is changed, or transaction is made,
    we have to store the comment content to permanent storage.

    To be saved in BigchainDB, possibly e-mailed, and posted on social media.
    """
    comment = models.ForeignKey(Comment)
    text = models.TextField()
    claimed_hours = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)
    assumed_hours = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)
    owner = models.ForeignKey(User)

    def __str__(self):
        return "Comment snapshot for {}".format(self.comment)


HOUR_PRICE_SOURCES = {
    'FRED': 'https://api.stlouisfed.org/fred/series/observations?series_id=CES0500000003&api_key=0a90ca7b5204b2ed6e998d9f6877187e&limit=1&sort_order=desc&file_type=json'
}

CURRENCY_PRICE_SOURCES = {
    'FIXER': 'https://api.fixer.io/latest?base=eur'
}


class Currency(GenericModel):
    """
    Currency labels, e.g. 'EUR', 'CNY', 'USD'.
    """
    label = models.CharField(max_length=10)

    def save(self, *args, **kwargs):
        """
        Save in upper case.
        """
        self.label = self.label.upper()
        super(Currency, self).save(*args, **kwargs)

    def in_hours(self,
                 hour_price_obj=None,
                 currency_price_obj=None,
                 hour_price_source='FRED',
                 currency_price_source='FIXER',
                 objects=False):
        """
        Compute the value of currency in hours.
        """

        if not hour_price_obj:
            hour_price_obj = HourPriceSnapshot.objects.filter(
                name=hour_price_source,
            ).last()

        if not currency_price_obj:
            currency_price_obj = CurrencyPriceSnapshot.objects.filter(
                name=currency_price_source
            ).last()

        if hour_price_obj.name =='FRED' and \
            currency_price_obj.name=='FIXER':


            rates = currency_price_obj.data['rates']
            rates[currency_price_obj.base.label] = 1.

            price = Decimal(hour_price_obj.data['observations'][0]['value'])
            hour_base_rate = Decimal(rates[hour_price_obj.base.label])
            local_base_rate = Decimal(rates[self.label])

            value = Decimal(1)/((price/hour_base_rate)*local_base_rate)

            if objects:
                return {
                    "in_hours": value,
                    "hour_price_snapshot": hour_price_obj,
                    "currency_price_snapshot": currency_price_obj
                }

            return value

    def __str__(self):
        return self.label

    class Meta:
        verbose_name_plural = "currencies"


class HourPriceSnapshot(GenericModel):
    """
    We need average price of human labor.

    Example:

    name = 'FRED'
    base = 'USD'
    endpoint = 'https://api.stlouisfed.org/fred/series/observations?series_id=CES0500000003&api_key=0a90ca7b5204b2ed6e998d9f6877187e&limit=1&sort_order=desc&file_type=json'
    """
    name = models.CharField(max_length=10)
    base = models.ForeignKey(Currency)

    endpoint = models.TextField()
    data = JSONField()

    def __str__(self):
        return self.name


class CurrencyPriceSnapshot(GenericModel):
    """
    We need the prices of currencies.

    Example:

    name = 'FIXER'
    base = 'EUR'
    endpoint = 'https://api.fixer.io/latest?base=hur'
    """
    name = models.CharField(max_length=10)
    base = models.ForeignKey(Currency)

    endpoint = models.TextField()
    data = JSONField()

    def __str__(self):
        return self.name


class Interaction(GenericModel):
    """
    Interactions are a way to invest time, parts of comments.

    They are actions of claiming time - claimed_hours, assumed_hours.
    """

    comment = models.ForeignKey(Comment)
    snapshot = models.ForeignKey(CommentSnapshot)

    claimed_hours_to_match = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)


class Transaction(GenericModel):
    """
    Transactions are a way to invest money to claimed time and things.

    They are actions of covering time - matched_hours, donated_hours.
    """

    comment = models.ForeignKey(Comment)
    snapshot = models.ForeignKey(CommentSnapshot)
    hour_price = models.ForeignKey(HourPriceSnapshot)
    currency_price = models.ForeignKey(CurrencyPriceSnapshot)

    payment_amount = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)
    payment_currency = models.ForeignKey(Currency)
    payment_recipient = models.ForeignKey(User, related_name='recipient')
    payment_sender = models.ForeignKey(User, related_name='sender')
    hour_unit_cost = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)

    donated_hours = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)
    matched_hours = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)

    def save(self, *args, **kwargs):
        """
        Save comment created date to parent object.
        """
        self.set_hours()
        super(Transaction, self).save(*args, **kwargs)
        self.create_contribution_certificates()

    def set_hours(self):
        """ Hours matched up with claimed time. """
        paid_in_hours = self.payment_amount/self.hour_unit_cost


        # self.matched_hours = min(self.snapshot.claimed_hours, paid_in_hours)
        remaining_claimed_time = self.comment.claimed_hours - self.comment.matched()
        self.matched_hours = min(remaining_claimed_time, paid_in_hours)

        """ Hours not matched up.  """
        # self.donated_hours = min(self.snapshot.assumed_hours, paid_in_hours - self.matched_hours)
        remaining_assumed_time = self.comment.assumed_hours - self.comment.donated()
        self.donated_hours = min(remaining_assumed_time, paid_in_hours - self.matched_hours)

    def create_contribution_certificates(self):
        """
        Subject: comment's remaining claimed_time, and assumed_time.
        ============================================================
        remaining_claimed_time , remaining_assumed_time
        """
        remaining_claimed_time = self.comment.claimed_hours - self.comment.matched()
        remaining_assumed_time = self.comment.assumed_hours - self.comment.donated()



        DOER = 0
        INVESTOR = 1

        if self.matched_hours:
            doer_cert = ContributionCertificate(
                type=DOER,
                transaction=self,
                comment_snapshot=self.snapshot,
                hours=self.matched_hours/Decimal(2.),
                matched=True,
                received_by=self.payment_recipient,
            )
            doer_cert.save()
            investor_cert = ContributionCertificate(
                type=INVESTOR,
                transaction=self,
                comment_snapshot=self.snapshot,
                hours=self.matched_hours/Decimal(2.),
                matched=True,
                received_by=self.payment_sender,
            )
            investor_cert.save()

        if self.donated_hours:
            doer_cert = ContributionCertificate(
                type=DOER,
                transaction=self,
                comment_snapshot=self.snapshot,
                hours=self.donated_hours/Decimal(2.),
                matched=False,
                received_by=self.payment_recipient,
            )
            doer_cert.save()
            investor_cert = ContributionCertificate(
                type=INVESTOR,
                transaction=self,
                comment_snapshot=self.snapshot,
                hours=self.donated_hours/Decimal(2.),
                matched=False,
                received_by=self.payment_sender,
            )
            investor_cert.save()


class ContributionCertificate(GenericModel):
    """
    ContributionCertificates are proofs of co-creation, grounded in
    immutable comment_snapshots and transactions: one doer, one investor.

    They will be e-mailed to both parties, in additional e-mail addresses
    desired, as well as in blockchains, so as to have multi-method prov-
    ability. ( https://infty.xyz/goal/116/detail/?lang=en )

    Additionally, users will be able to provide social media accounts to
    post their updates of ContributionCertificates.

    Regarding the .matched property -- indicates if the time was matched.
      Instead of updating the record, we will create new contribution
      certificates. If a transaction certificate is updated, derived
      future is considered invalid.

    Whenever we have a contribution certificate with matched=False time,

    """
    DOER = 0
    INVESTOR = 1

    CERTIFICATE_TYPES = [
        (DOER, 'DOER'),
        (INVESTOR, 'INVESTOR'),
    ]

    type = models.PositiveSmallIntegerField(CERTIFICATE_TYPES, default=DOER)
    transaction = models.ForeignKey(Transaction)
    interaction = models.ForeignKey(Interaction, blank=True, null=True)
    comment_snapshot = models.ForeignKey(CommentSnapshot)
    hours = models.DecimalField(default=0.,decimal_places=8,max_digits=20,blank=False)
    matched = models.BooleanField(default=True)
    received_by = models.ForeignKey(User)

    broken = models.BooleanField(default=False)
    parent = models.ForeignKey('self', blank=True, null=True)


    @classmethod
    def user_matched(cls, user):
        """
        Returns amount of matched hours that a given user has accumulated.
        """
        return Decimal(
            cls.objects.filter(
                matched=True,
                broken=False,
                received_by=user).aggregate(
                    total=Sum('hours')
                ).get('total')
            or 0)

    @classmethod
    def user_unmatched(cls, user):
        """
        Returns amount of matched hours that a given user has accumulated.
        """
        return Decimal(
            cls.objects.filter(
                matched=False,
                broken=False,
                received_by=user).aggregate(
                    total=Sum('hours')
                ).get('total')
            or 0)