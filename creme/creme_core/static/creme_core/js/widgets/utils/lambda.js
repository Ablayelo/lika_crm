/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2013  Hybird

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

creme.utils = creme.utils || {};

creme.utils.Lambda = creme.component.Component.sub({
    _init_: function(callable, parameters) {
        this.lambda(callable, parameters);
    },

    isValid: function() {
        return !Object.isNone(this._lambda)
    },

    apply: function(context, parameters) {
        if (this._lambda) {
            return this._lambda.apply(context, parameters);
        }
    },

    call: function()
    {
        if (this._lambda) {
            var args = Array.copy(arguments);
            return this._lambda.apply(args[0], args.slice(1));
        }
    },

    invoke: function() {
        return this._lambda ? this._lambda.apply(this._context || this, arguments) : undefined;
    },

    constant: function(value)
    {
        this._lambda = function() {return value;};
        return this;
    },

    lambda: function(callable, parameters)
    {
        if (callable === undefined)
            return this._lambda;

        if (Object.isFunc(callable)) {
            this._lambda = callable;
            return this;
        }

        if (!Object.isType(callable, 'string'))
            return this.constant(callable);

        if (Object.isEmpty(callable))
            throw Error('empty lambda script');

        var parameters = Array.isArray(parameters) ? parameters.join(',') : (parameters || '');
        var uuid = $.uidGen({prefix: '__lambda_', mode:'random'});

        var script = 'creme.utils["' + uuid + '"] = function(' + parameters + ') {';
        script += callable.indexOf('return') != -1 ? callable : 'return ' + callable + ';';
        script += '};';

        eval(script);

        this._lambda = creme.utils[uuid];
        delete creme.utils[uuid];

        return this;
    },

    callable: function() {
        return this._context ? this._lambda.bind(this._context) : this._lambda;
    },

    bind: function(context)
    {
        this._context = context;
        return this;
    }
});

creme.utils.lambda = function(callable, parameters, defaults)
{
    try {
        return new creme.utils.Lambda(callable, parameters).callable();
    } catch(e) {
        if (defaults !== undefined)
            return defaults;

        throw e;
    }
}
