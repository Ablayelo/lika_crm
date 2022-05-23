/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022  Hybird

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

(function($) {
"use strict";

/* TODO: unit test */
/* TODO: button to de-select all? */
/* TODO: input to search/filter in choices? */
creme.widget.SelectOrInputWidget = creme.widget.declare('ui-creme-ordered', {
    _create: function(element, options) {
        this._targetInput = element.find('.ordered-widget-value');
        this._availableContainer = element.find('.ordered-widget-available-choices');
        this._enabledContainer = element.find('.ordered-widget-enabled-choices');

        // TODO: if empty...
        var choices = JSON.parse(creme.utils.JSON.readScriptText(element.find('.ordered-widget-choices')));

        var selected = JSON.parse(this._targetInput.val());
        if (!Array.isArray(selected)) {
            throw new Error('SelectOrInputWidget: invalid selected values', selected);
        }

        selected.forEach(
            function(selected_id) {
                var index = choices.findIndex(function(choice) {
                    return (choice[0] === selected_id);
                });

                this._enabledContainer.append(this._buildEntry(choices[index]));
                choices.splice(index, 1);  // We remove the choice from the available ones.
            }.bind(this)
        );
        choices.forEach(
            function(choice) {
                this._availableContainer.append(this._buildEntry(choice));
            }.bind(this)
        );

        var sortableOptions = {group: element.attr('id'), dataIdAttr: 'data-choice-id'};
        this._availableChoices = new Sortable(
            this._availableContainer.get(0), $.extend({sort: false}, sortableOptions)
        );
        this._enabledChoices = new Sortable(
            this._enabledContainer.get(0), $.extend({onSort: this._updateValue.bind(this)}, sortableOptions)
        );

        element.addClass('widget-ready');
    },

    _buildEntry: function(choice) {
        // TODO: description if available
        return $('<div>').attr('class', 'ordered-widget-choice')
                         .attr('data-choice-id', choice[0])
                         .text(choice[1])
                         .dblclick(this._transferChosen.bind(this));
    },

    _updateValue: function() {
        this._targetInput.val(JSON.stringify(this._enabledChoices.toArray()));
    },

    _transferChosen: function(event) {
        var entryDiv = $(event.target);
        var parent = entryDiv.parent('.ordered-widget-choices');

        entryDiv.remove();

        if (parent.hasClass('ordered-widget-enabled-choices')) {
            this._availableContainer.append(entryDiv);
        } else {
            this._enabledContainer.append(entryDiv);
        }

        this._updateValue();
    }
});

}(jQuery));
