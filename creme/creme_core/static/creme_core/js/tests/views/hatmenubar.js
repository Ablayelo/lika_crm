/* globals QUnitListViewMixin QUnitWidgetMixin */

(function($) {

QUnit.module("creme.detailview.hatmenubar", new QUnitMixin(QUnitEventMixin,
                                                           QUnitAjaxMixin,
                                                           QUnitDialogMixin,
                                                           QUnitListViewMixin,
                                                           QUnitWidgetMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        var selectionListHtml = this.createListViewHtml(this.defaultListViewHtmlOptions({
            id: 'selection-list'
        }));

        this.setListviewReloadContent('selection-list', selectionListHtml);

        this.setMockBackendGET({
            'mock/relation/selector': backend.response(200, selectionListHtml)
        });

        this.setMockBackendPOST({
            'mock/relation/add': backend.response(200, '')
        });

        $('body').attr('data-save-relations-url', 'mock/relation/add');
        $('body').attr('data-select-relations-objects-url', 'mock/relation/selector');
    },

    afterEach: function() {
        creme.widget.shutdown($('body'));
    },

    createHatMenuBarHtml: function(options) {
        options = $.extend({
            buttons: []
        }, options || {});

        var html = (
            '<div widget="ui-creme-hatmenubar" class="ui-creme-hatmenubar ui-creme-widget">' +
                '${buttons}' +
            '</div>').template({
                buttons: (options.buttons || []).join('')
            });

        return html;
    },

    createHatMenuBar: function(options) {
        var html = this.createHatMenuBarHtml(options);

        var element = $(html).appendTo($('body'));
        var widget = creme.widget.create(element);

        this.assertActive(element);
        this.assertReady(element);

        return widget;
    },

    createHatMenuActionButton: function(options) {
        return (
            '<a href="${url}" data-action="${action}" class="menu_button">' +
                '<script type="application/json"><!-- ${data} --></script>' +
            '</a>').template({
                url: options.url,
                action: options.action,
                data: $.toJSON({
                    data: options.data || {},
                    options: options.options || {}
                })
            });
    }
}));

QUnit.test('creme.detailview.hatmenubar (empty)', function(assert) {
    var element = $(this.createHatMenuBarHtml()).appendTo($('body'));

    element.on('hatmenubar-setup-actions', this.mockListener('hatmenubar-setup-actions'));

    var widget = creme.widget.create(element);
    var builder = widget.delegate._builder;

    deepEqual([['hatmenubar-setup-actions', [builder]]], this.mockListenerJQueryCalls('hatmenubar-setup-actions'));
});

QUnit.test('creme.detailview.hatmenubar (no action)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: ['<a class="menu_button"/>']
    });

    deepEqual([], widget.delegate._actionlinks);
});

QUnit.test('creme.detailview.hatmenubar (addrelationships)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: '/mock/relation/add',
                action: 'creme_core-hatmenubar-addrelationships',
                data: {
                    subject_id: '74', rtype_id: 'rtypes.1', objects_ct_id: '5'
                }
            })
        ]
    });

    deepEqual(1, widget.delegate._actionlinks.length);

    var link = widget.delegate._actionlinks[0];

    equal(true, link.isBound());
    equal(false, link.isDisabled());

    $(widget.element).find('a.menu_button').click();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', whoami: '1000'}]
    ], this.mockBackendUrlCalls('mock/relation/selector'));

    var list = this.assertOpenedListViewDialog().data('list_view');

    this.setListviewSelection(list, ['2', '3']);

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.submitListViewSelectionDialog(list);
    this.assertClosedDialog();

    deepEqual([
        ['GET', {subject_id: '74', rtype_id: 'rtypes.1', whoami: '1000'}],
        ['POST', {entities: ['2', '3'], predicate_id: 'rtypes.1', subject_id: '74'}]
    ], this.mockBackendUrlCalls());
});

}(jQuery));