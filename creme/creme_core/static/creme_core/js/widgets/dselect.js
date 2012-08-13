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

creme.widget.DynamicSelect = creme.widget.declare('ui-creme-dselect', {
    options: {
        url: '',
        backend: new creme.ajax.Backend({dataType:'json', sync:true}),
        datatype: 'string'
    },

    _create: function(element, options, cb, sync)
    {
        this._initial = element.html();
        this._url = new creme.string.Template(options.url);
        this._fill(element, this.url(element), cb, undefined, sync);
    },

    _update_disabled_state: function(element) {
        ($('option', element).length > 1) ? element.removeAttr('disabled') : element.attr('disabled', 'disabled');
    },

    url: function(element) {
        return this._url.render();
    },

    dependencies: function(element) {
        return this._url.tags();
    },

    reload: function(element, data, cb, error_cb, sync)
    {
        this._url.update(data);
        this._fill(element, this.url(element), cb, error_cb, sync);
    },

    update: function(element, data)
    {
       var self = this;
       data = creme.widget.parseval(data, creme.ajax.json.parse);

       if (typeof data !== 'object' || data === null)
          return;

       var selected = data['value'];
       var added_items = data['added'] !== undefined ? data['added'] : [];
       var removed_items = data['removed'] !== undefined ? data['removed'] : [];

       for (var i = 0; i < removed_items.length; ++i) {
           var removed = removed_items[i];
           $('option[value="' + removed + '"]', element).detach();
       }

       for (var i = 0; i < added_items.length; ++i) {
           var added = added_items[i];
           element.append($('<option/>').val(added[0]).text(added[1]));
       }

       self.val(element, selected);
       self._update_disabled_state(element);
    },

    _fill_begin: function(element) {
        element.removeClass('widget-ready');
    },

    _fill_end: function(element, old) {
        element.addClass('widget-ready');
        this._triggerchanged(element, old);
    },

    _triggerchanged: function(element, old)
    {
        if (this.val(element) !== old) {
            // Chrome behaviour (bug ?) : select value is not updated if disabled.
            // so enable it before change value !
            element.removeAttr('disabled');
            element.change();
        }

        this._update_disabled_state(element);
    },

    _staticfill: function(element, data) {
        creme.forms.Select.fill(element, data);
    },

    _ajaxfill: function(element, url, cb, error_cb, sync)
    {
        var self = this;
        var old = this.val(element)

        if (creme.object.isempty(url))
        {
            element.empty();
            element.html(self._initial);
            self._fill_end(element, old);
            creme.object.invoke(error_cb, element, new creme.ajax.AjaxResponse('404', ''));
            return;
        }

        this.options.backend.get(url, {fields:['id', 'unicode']},
                                 function(data) {
                                     self._staticfill(element, data);
                                     self._fill_end(element, old);
                                     creme.object.invoke(cb, element);
                                 },
                                 function(data, error) {
                                     element.empty();
                                     element.html(self._initial);
                                     self._fill_end(element, old);
                                     creme.object.invoke(error_cb, element, error);
                                 },
                                 {sync:sync});
    },

    _fill: function(element, data, cb, error_cb, sync)
    {
        var self = this;

        if (creme.object.isnone(data) === true) {
            creme.object.invoke(cb, element);
            return;
        }

        self._fill_begin(element);

        if (typeof data === 'string') {
            self._ajaxfill(element, data, cb, error_cb, sync);
            return;
        }

        if (typeof data === 'array') {
            self._staticfill(element, data);
        }

        self._fill_end(element);
        creme.object.invoke(cb, element);
    },

    val: function(element, value)
    {
        if (value === undefined)
            return element.val();

        var old = element.val();

        if (typeof value !== 'string')
            value = $.toJSON(value);

        element.val(value);
        this._triggerchanged(element, undefined);
    },

    cleanedval: function(element)
    {
        var value = this.val(element);

        if (this.options.datatype == 'string')
            return value;

        return creme.widget.cleanval(value, value);
    },

    choice: function(element, key)
    {
        if (creme.object.isempty(key) === false)
            return [key, $('> option[value="' + key + '"]', element).text()];
    },

    choices: function(element)
    {
        var choices = [];

        $('> option', element).each(function() {
            choices.push([$(this).attr('value'), $(this).text()]);
        });

        return choices;
    },

    selected: function(element) {
        return this.choice(element, this.val(element));
    }
});

//(function($) {
//    $.widget("ui.dselect", creme.widget.dselect);
//})(jQuery);
