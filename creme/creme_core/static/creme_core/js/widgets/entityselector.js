/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2012  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

creme.widget.ENTITY_SELECT_BACKEND = new creme.ajax.CacheBackend(new creme.ajax.Backend(),
                                                                 {condition: new creme.ajax.CacheBackendTimeout(120 * 1000)});

creme.widget.EntitySelectorMode = {
    MULTIPLE: 0,
    SINGLE: 1
};

creme.widget.EntitySelector = creme.widget.declare('ui-creme-entityselector', {

    options : {
        popupURL: '',
        popupSelection: creme.widget.EntitySelectorMode.SINGLE,
        popupAuto: undefined,
        labelURL: '',
        label: gettext('Select'),
        qfilter: '',
        backend: creme.widget.ENTITY_SELECT_BACKEND
    },

    _create: function(element, options, cb, sync)
    {
        var self = this;

        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');

        if (!this._enabled) {
            $(element).attr('disabled', '');
            $('button', element).attr('disabled', '');
        }

        $(element).bind('click', function() {
            if (self._enabled) {
                self._select(element, $(this));
            }
        });

        this

        $(element).bind('selectorlist-added', function(e, selector) {
            self._autoselect(element);
        });

        var selection = creme.widget.cleanval(options.popupSelection, creme.widget.EntitySelectorMode.SINGLE);

        this._popupURL = new creme.string.Template(options.popupURL, {
                                                       qfilter: options.qfilter,
                                                       selection: selection
                                                   });

        this._isPopupAuto = !Object.isNone(options.popupAuto)

        this._reloadLabel(element, cb, undefined, sync);
        element.addClass('widget-ready');
    },

    dependencies: function(element) {
        return this._popupURL.tags();
    },

    reload: function(element, data, cb, error_cb, sync)
    {
        this._popupURL.update(data);
        this.val(element, null);
        creme.object.invoke(cb, element);
    },

    update: function(element, data)
    {
        var self = this;

        if (typeof data === 'string')
            data = creme.widget.parseval(data, creme.ajax.json.parse);

        if (typeof data !== 'object')
            return;

        var selected = data['value'];
        self.val(element, selected);
    },

    _update: function(element, values)
    {
        this.val(element, values[0]);

        // TODO : hack that automatically add lines when multiselection is enabled
        if (this.isMultiple(element) && (values.length > 1))
        {
            var list = this.parentSelectorList(element).creme().widget();
            var chainname = element.parent().attr('chained-name');
            var chain = chainname ? element.parents('.ui-creme-chainedselect:first').creme().widget() : undefined;

            if (creme.object.isempty(list))
                return;

            if (creme.object.isempty(chain)) {
                for(var index = 1; index < values.length; ++index) {
                    var selector = list.appendSelector(values[index]);
                }
            } else {
                var data = creme.widget.cleanval(chain.val());

                for(var index = 1; index < values.length; ++index) {
                    data[chainname] = values[index];
                    var selector = list.appendSelector(data);
                }
            }
        }
    },

    _autoselect: function(element)
    {
        var self = this;

        if (this._isPopupAuto && Object.isEmpty(this.val(element)))
        {
            this._select(element, function(element, result) {
                if (Object.isEmpty(self.val(element))) {
                    self.parentSelectorList(element).creme().widget().removeSelector(element);
                }
            });
        }
    },

    _select: function(element, cb)
    {
        var self = this;
        var url = this.popupURL(element);

        // TODO : fix a bug in server view that doesn't accept empty q_filter
        if (creme.object.isempty(this._popupURL.parameters.qfilter))
            url = url.replace('?q_filter=', '');

        creme.utils.showInnerPopup(url, {
                                    send_button_label: gettext("Validate the selection"),
                                    send_button: function(dialog) {
                                            var lv = $('form[name="list_view_form"]');
                                            var result = lv.list_view("getSelectedEntitiesAsArray");

                                            if (result.length == 0) {
                                                creme.utils.showDialog(gettext("Please select at least one entity."), {'title': gettext("Error")});
                                                return;
                                            }

                                            self._update(element, result);
                                            creme.utils.closeDialog(dialog, false);
                                            creme.object.invoke(cb, element, result);
                                        },
                                    cancel: function(ui) {
                                        creme.object.invoke(cb, element);
                                    }
                                   });
    },

    _reloadLabel: function(element, on_success, on_error, sync)
    {
        var options = this.options;
        var button = $('button', element);
        var value = creme.widget.input(element).val();

        if (creme.object.isempty(value) === true)
        {
            button.text(options.label);
            creme.object.invoke(on_success, element);
            return;
        }

        var url = creme.widget.template(options.labelURL, {'id': value});

        options.backend.get(url, {fields:['unicode']},
                            function(data, status) {
                                button.text(data[0][0]);
                                creme.object.invoke(on_success, element, data);
                            },
                            function(data, error) {
                                button.text(options.label);
                                creme.object.invoke(on_error, element, error);
                            },
                            {dataType:'json', sync:sync});
    },

    isMultiple: function(element) {
        return this._popupURL.parameters.selection === creme.widget.EntitySelectorMode.MULTIPLE;
    },

    multiple: function(element, value) {
        var value = value ? creme.widget.EntitySelectorMode.MULTIPLE : creme.widget.EntitySelectorMode.SINGLE;
        this._popupURL.update({selection:value});
    },

    parentSelectorList: function(element) {
        return element.parents('.ui-creme-selectorlist:first');
    },

    qfilter: function(element, value) {
        this._popupURL.update({qfilter:value});
    },

    popupURL: function(element) {
        return this._popupURL.render();
    },

    reset: function(element) {
        this.val(element, null);
    },

    val: function(element, value)
    {
        if (value === undefined)
            return creme.widget.input(element).val();

        creme.widget.input(element).val(value);
        this._reloadLabel(element);
        element.trigger('change');
    },

    cleanedval: function(element)
    {
        var value = this.val(element);
        return creme.object.isempty(value) ? null : value;
    }
});
