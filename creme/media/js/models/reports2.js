/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2010  Hybird

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

/*
 * Requires : creme, jQuery, creme.utils, creme.ajax
 */

if(!creme.reports) creme.reports = {};

creme.reports.loading_options = {
    beforeSend : function(request){
          creme.utils.loading('loading', false, {});
      },
    complete:function (XMLHttpRequest, textStatus) {
          creme.utils.loading('loading', true, {});
      }
};


creme.reports.load = function(options)
{
    if(!options || options == undefined) return;

    var ct_id = $(options.ct).val();
    if(!ct_id || ct_id =="")
    {
        $(options.show_after_ct).hide();
        return;
    }

    var $hf   = $(options.hf);
    this.loadHeaderFilters(ct_id, $hf);

    var $filter   = $(options.filter);
    this.loadFilters(ct_id, $filter);

    this.loadColumns(ct_id, options);
    this.loadCf(ct_id, options);
    this.loadRelations(ct_id, options);
    this.loadFunctions(ct_id, options);

    $(options.show_after_ct).show();
}

//Could use creme.forms.Select.optionsFromData & creme.forms.Select.fill with a hack for default/error options?
creme.reports.__loadFilters = function(url, ct_id, $target_select, parameters)
{
    if($target_select.size() != 1) return;

    var params = $.extend({
        'err_label' : 'Aucun disponible',//TODO:i18n
        'always_option': null,//Always the 1st <option /> in non-empty success cases
        'empty_option' : null,
        'error_option' : null
    }, parameters);

    var $def_option = $('<option value="">'+params.err_label+'</option>');

    var success_cb = function(data, textStatus, req){
        $target_select.empty();

        if(data.length == 0 && !params.empty_option){
            $target_select.append($def_option);
        }
        if(data.length == 0 && params.empty_option){
            $target_select.append(params.empty_option);
        }
        if(data.length > 0 && params.always_option)
        {
            $target_select.append(params.always_option);
        }

        for(var i in data)
        {
            var d = data[i];
            $target_select.append($('<option value="'+d.pk+'">'+d.fields.name+'</option>'));
        }
    };

    var error_cb = function(req, textStatus, err){
        if(!params.err_option)
        {
            $target_select.empty().append($def_option);
        }
        else
        {
            $target_select.empty().append(params.empty_option);
        }
    };

    creme.ajax.json.get(url, {}, success_cb, error_cb, false, this.loading_options);
}

creme.reports.loadHeaderFilters = function(ct_id, $target_select)
{
    var url = '/creme_core/header_filter/get_4_ct/'+ct_id;
    var params = {
        'always_option': $('<option value="">Aucune vue sélectionnée</option>')
    };
    creme.reports.__loadFilters(url, ct_id, $target_select, params);
}

creme.reports.loadFilters = function(ct_id, $target_select)
{
    var url = '/creme_core/filter/get_4_ct/'+ct_id;

    var $all_opt = $('<option value="">Tout</option>');

    var params = {
        'empty_option' : $all_opt,
        'always_option': $all_opt,
        'error_option' : $all_opt
    };

    creme.reports.__loadFilters(url, ct_id, $target_select, params);
}

creme.reports.__loadOrderedMultiSelect = function(url, pdata, table_id, input_name)
{

    var $columns_table = $('#'+table_id);
    if($columns_table.size() !=1) return;

    var $tbody = $columns_table.find('tbody');

    var success_cb = function(data, textStatus, req){
        $tbody.empty();
        $columns_table.parent('.oms_div').children().not($columns_table).remove();

        for(var i in data)
        {
            var d = data[i];
            var val = d[0];
            var txt = d[1];

            var $tr = $('<tr />').attr('name', 'oms_row_'+i);

            var $td1 = $('<td><input class="oms_check" type="checkbox" name="'+input_name+'_check_'+i+'" /></td>');
            var $td2 = $('<td class="oms_value">'+txt+'<input type="hidden" value="'+val+'" name="'+input_name+'_value_'+i+'"/></td>');
            var $td3 = $('<td><input class="oms_order" type="text" name="'+input_name+'_order_'+i+'" value=""/></td>');

            $tbody.append($tr.append($td1).append($td2).append($td3));
        }
        creme.forms.toOrderedMultiSelect(table_id);
    };

    var error_cb = function(req, textStatus, err){
        $tbody.empty();
        $columns_table.parent('.oms_div').children().not($columns_table).remove();
    };

    creme.ajax.json.post(url, pdata, success_cb, error_cb, false, this.loading_options);

}

creme.reports.loadColumns = function(ct_id, options)
{
    creme.reports.__loadOrderedMultiSelect('/creme_core/get_fields',
                                           {'ct_id': ct_id},
                                           options.columns.table_id,
                                           options.columns.name);
}

creme.reports.loadCf = function(ct_id, options)
{
    creme.reports.__loadOrderedMultiSelect('/creme_core/get_custom_fields',
                                       {'ct_id': ct_id},
                                       options.cf.table_id,
                                       options.cf.name);
}

creme.reports.loadRelations = function(ct_id, options)
{
    creme.reports.__loadOrderedMultiSelect('/creme_core/relation/get_predicates_choices_4_ct',
                                       {'ct_id': ct_id},
                                       options.relations.table_id,
                                       options.relations.name);
}

creme.reports.loadFunctions = function(ct_id, options)
{
    creme.reports.__loadOrderedMultiSelect('/creme_core/get_user_functions',
                                       {'ct_id': ct_id},
                                       options.functions.table_id,
                                       options.functions.name);
}

creme.reports.unlink_report = function(field_id, block_url)
{
    var success_cb = function(data, textStatus, req)
    {
        if(block_url && block_url != undefined)
        {
            creme.utils.loadBlock(block_url);
        }
    };

    var error_cb = function(req, textStatus, err)
    {
        
    };
    
    creme.ajax.json.post('/reports2/report/field/unlink_report', {'field_id': field_id}, success_cb, success_cb, false, this.loading_options);
}

creme.reports.link_report = function(report_id, field_id, block_url)
{
    creme.utils.innerPopupNReload('/reports2/report/'+report_id+'/field/'+field_id+'/link_report', block_url);
}

creme.reports.link_relation_report = function(report_id, field_id, predicate, block_url)
{
    var success_cb = function(data, textStatus, req)
    {
        var $select = $('<select />');
        creme.forms.Select.fill($select, [["","Sélectionnez un type"]].concat(data), "");
        
        creme.utils.showDialog($select, {
            buttons : {
                "Ok" : function(){
                    if($select.val() == "")
                    {
                        creme.utils.showDialog("Veuillez sélectionner un type.");
                        return;
                    }

                    creme.utils.innerPopupNReload('/reports2/report/'+report_id+'/field/'+field_id+'/link_relation_report/'+$select.val(), block_url);

                    $(this).dialog("close");
                }
            }
        });

    }

    var error_cb = function(req, textStatus, err)
    {
        
    }

    creme.forms.RelationSelector.contentTypeRequest(predicate, success_cb, error_cb);
}

creme.reports.changeOrder = function(report_id, field_id, direction, block_url)
{
    var success_cb = function(data, textStatus, req)
    {
        if(block_url && block_url != undefined)
        {
            creme.utils.loadBlock(block_url);
        }
    };

    var error_cb = function(req, textStatus, err)
    {
        //creme.utils.showDialog("Erreur, actualisez la page");
    };

    var data = {'report_id': report_id, 'field_id': field_id, 'direction': direction};

    creme.ajax.json.post('/reports2/report/field/change_order', data, success_cb, success_cb, false, this.loading_options);
}

creme.reports.setSelected = function(checkbox, report_id, field_id, block_url)
{
    var success_cb = function(data, textStatus, req)
    {
        if(block_url && block_url != undefined)
        {
            creme.utils.loadBlock(block_url);
        }
    };

    var error_cb = function(req, textStatus, err)
    {
        //creme.utils.showDialog("Erreur, actualisez la page");
    };

    var data = {'report_id': report_id, 'field_id': field_id, 'checked': +$(checkbox).is(':checked')};

    creme.ajax.json.post('/reports2/report/field/set_selected', data, success_cb, success_cb, false, this.loading_options);

};