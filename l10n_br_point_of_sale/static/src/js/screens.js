odoo.define('br_point_of_sale.screens', function (require) {
    "use strict";

    var pos_screens = require('point_of_sale.screens');

    pos_screens.PaymentScreenWidget.include({
        init: function(parent, options) {
            var self = this;
            this._super(parent, options);
            //Overide methods to user keyboard on popup
            this.keyboard_keydown_handler = function(event){
                if ($('.TextInputPopupWidget').on('keydown'))
                {

                }
                if (event.keyCode != 8 && event.keyCode != 110 && event.keyCode != 46) { // Backspace and dots
                    if (event.keyCode < 48 || (event.keyCode > 57 && event.keyCode < 96) || event.keyCode > 105){ // keyboard and numbpad numbers
                        event.preventDefault();
                        self.keyboard_handler(event);
                    }
                }
            };
            this.keyboard_handler = function(event){
                var key = '';
    
                if (event.type === "keypress") {
                    if (event.keyCode === 13) { // Enter
                        self.validate_order();
                    } else if ( event.keyCode === 190 || // Dot
                                event.keyCode === 110 ||  // Decimal point (numpad)
                                event.keyCode === 188 ||  // Comma
                                event.keyCode === 46 ) {  // Numpad dot
                        key = self.decimal_point;
                    } else if (event.keyCode >= 48 && event.keyCode <57) { // Numbers
                        key = '' + (event.keyCode - 48);
                    } else if (event.keyCode === 45) { // Minus
                        key = '-';
                    } else if (event.keyCode === 43) { // Plus
                        key = '+';
                    }
                } else { // keyup/keydown
                    if (event.keyCode === 46) { // Delete
                        key = 'CLEAR';
                    } else if (event.keyCode === 8) { // Backspace
                        key = 'BACKSPACE';
                    }
                }
            };
        },
        renderElement: function(){
            this._super()
            var self = this;
            this.$('.js_customer_cpf').ready(function($)
            {
                $('input[type=text][name=customer_cpf]').mask('000.000.000-00');
            });
            this.$('.js_customer_cpf').click(function(){
                self.click_set_customer_cpf();
            });
        },
        click_set_customer_cpf: function(){
            var order = this.pos.get_order();
            this.gui.show_popup('textinput',{
                'title': 'Input CPF',
                'confirm': function(value) {
                    order.set_client_cpf(value);
                }
            })
        },
    });

    let ajax = require('web.ajax');
    let clientScreen = require('point_of_sale.screens');

    let ClientListScreenWidget = clientScreen.ClientListScreenWidget.include({
        save_client_details: function(partner) {
            let self = this;
            let pessoa = this.$('.client-company:checked').val();
            this.$('input[name=is_company]').val(pessoa);
            return this._super(partner);
        },

        display_client_details: function(visibility, partner, clickpos){
            var self = this;
            let result = this._super(visibility, partner, clickpos);

            var contents = this.$('.client-details-contents');

            contents.off('click', '.button.searchzip');
            contents.off('change', 'select[name=country_id]');
            contents.off('change', 'select[name=state_id]');
            contents.on('click', '.button.searchzip', function () {
                self.search_zip_code(partner);
            });
            contents.on('change', 'select[name=country_id]', function () {
                self.search_states(partner);
            });
            contents.on('change', 'select[name=state_id]', function () {
                self.search_cities(partner);
            });
            if (visibility === "edit") {
                self.search_states(partner, true);
                self.search_cities(partner, true);
            }
            return result;
        },
        search_zip_code: function(partner) {
            var self = this;
            var zipcode = this.$('input[name="zip"]').val();
            var regex = /[^0-9]/g;
            zipcode = zipcode.replace(regex, '');

            ajax.jsonRpc('/contact/zip_search', 'call', {
                  zip: zipcode,
              }).then(function(result){
                  if(result.sucesso){
                      self.$('input[name="zip"]').val(zipcode.slice(0, 5) + '-' + zipcode.slice(5, 8));
                      self.$('input[name="street"]').val(result.street);
                      self.$('input[name="district"]').val(result.district);
                      self.$('select[name="city_id"]').val(result.city_id);
                      self.$('select[name="state_id"]').val(result.state_id);
                      self.$('select[name="country_id"]').val(result.country_id);
                      partner.state_id = [result.state_id, "temp"];
                      partner.city_id = [result.city_id, "temp"];
                      self.search_states(partner);
                  }else {
                      alert('Nenhum CEP encontrado!');
                  }
              }, function(err,ev){
                  alert('Erro ao pesquisar CEP');
              });
        },
        search_states: function (partner, force) {
            var country = $('select[name=country_id]').val();
            if (force) {
                country = partner.country_id && partner.country_id[0] || 0;
            };
            var vals = {country_id: parseInt(country)};
            ajax.jsonRpc("/contact/get_states", 'call', vals).then(
                function (data) {
                    var selected = partner.state_id && partner.state_id[0] || 0;
                    $('select[name=state_id]').find('option').remove().end();
                    $('select[name=state_id]').append(
                        '<option value="">Estado...</option>');
                    $.each(data, function (i, item) {
                        $('select[name=state_id]').append($('<option>', {
                            value: item[0],
                            text: item[1],
                            selected: item[0]===selected?true:false,
                        }));
                    });
                  $('select[name=state_id]').trigger('change');
              });
        },
        search_cities: function (partner, force) {
            var state = $('select[name=state_id]').val();
            if (force) {
                state = partner.state_id && partner.state_id[0] || 0;
            };
            var vals = {state_id: parseInt(state)};
            ajax.jsonRpc("/contact/get_cities", 'call', vals).then(
                function (data) {
                    var selected = partner.city_id && partner.city_id[0] || 0;
                    $('select[name=city_id]').find('option').remove().end();
                    $('select[name=city_id]').append(
                        '<option value="">Cidade...</option>');
                    $.each(data, function (i, item) {
                        $('select[name=city_id]').append($('<option>', {
                            value: item[0],
                            text: item[1],
                            selected: item[0]===selected?true:false,
                        }));
                    });
                }
            );
        },
    });

    return ClientListScreenWidget;


});
