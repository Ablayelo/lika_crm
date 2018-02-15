# -*- coding: utf-8 -*-

already_run = False


def ready():
    global already_run

    if already_run:
        return

    already_run = True

    from ..gui import (brick_registry, import_form_registry,
            merge_form_registry, quickforms_registry, smart_columns_registry)
    from ..registry import creme_registry

    from .fake_bricks import FakeAppPortalBrick
    from .fake_constants import FAKE_REL_SUB_EMPLOYED_BY
    from .fake_forms import (FakeContactQuickForm, FakeOrganisationQuickForm,
            get_csv_form_builder, get_merge_form_builder)
    from .fake_models import (FakeContact, FakeOrganisation, FakeImage,
            FakeActivity, FakeEmailCampaign, FakeMailingList, FakeInvoice, FakeInvoiceLine)

    from creme.creme_config.tests.fake_models import FakeConfigEntity

    creme_registry.register_entity_models(FakeContact,
                                          FakeOrganisation,
                                          FakeImage,
                                          FakeActivity,
                                          FakeEmailCampaign,
                                          FakeMailingList,
                                          FakeInvoice,
                                          FakeInvoiceLine,
                                          FakeConfigEntity,
                                         )

    brick_registry.register(FakeAppPortalBrick)
    brick_registry.register_invalid_models(FakeInvoiceLine)  # See creme_config tests

    reg_qform = quickforms_registry.register
    reg_qform(FakeContact,      FakeContactQuickForm)
    reg_qform(FakeOrganisation, FakeOrganisationQuickForm)

    smart_columns_registry.register_model(FakeContact) \
                          .register_field('first_name') \
                          .register_field('last_name') \
                          .register_relationtype(FAKE_REL_SUB_EMPLOYED_BY)

    reg_csv_form = import_form_registry.register
    reg_csv_form(FakeContact,      get_csv_form_builder)
    reg_csv_form(FakeOrganisation, get_csv_form_builder)

    reg_merge_form = merge_form_registry.register
    reg_merge_form(FakeContact,      get_merge_form_builder)
    reg_merge_form(FakeOrganisation, get_merge_form_builder)
