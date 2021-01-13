import re
import base64
from pytrustnfe.nfse.ginfes import recepcionar_lote_rps, consultar_situacao_lote,  cancelar_nfse, consultar_lote_rps
from pytrustnfe.certificado import Certificado

import logging
import json
import datetime

_logger = logging.getLogger(__name__)


def _convert_values(vals):
    _logger.error('vals: %s' % ( json.dumps(vals),))
    result = {'lista_rps': vals}

    # numero_lote
    # result['numero_lote'] = datetime.datetime.now().timestamp()
    result['numero_lote'] = vals[0]['numero_rps']
    result['cnpj_prestador'] = vals[0]['emissor']['cnpj']
    result['inscricao_municipal'] = vals[0]['emissor']['inscricao_municipal']

    for rps in vals:
        rps['data_emissao'] = datetime.datetime.now().replace(microsecond=0).isoformat()
        rps['numero'] = rps['numero_rps']
        rps['optante_simples'] = 1 if rps['regime_tributario'] == "simples" else 2
        # TODO: Talvez SBC retenha quando a nota vai para SBC (confirmar com contador)
        rps['iss_retido'] = 1 if rps['iss_retido'] else 2

        # TODO: pegar de algum lugar
        # Código de Tributação no Município
        rps['codigo_tributacao_municipio'] = rps['itens_servico'][0]['codigo_servico_municipio']
        rps['valor_iss_retido'] = rps['iss_valor_retencao']
        rps['valor_deducao'] = 0
        rps['valor_pis'] = 0
        rps['valor_cofins'] = 0
        rps['valor_inss'] = 0
        rps['valor_ir'] = 0
        rps['valor_csll'] = 0
        rps['outras_retencoes'] = 0
        rps['desconto_incondicionado'] = 0
        rps['desconto_condicionado'] = 0

        rps['aliquota_issqn'] = rps['itens_servico'][0]['aliquota']
        rps['valor_iss'] =  rps['aliquota_issqn'] * rps['valor_servico']
        rps['valor_liquido_nfse'] = rps['valor_servico'] \
            - rps['valor_pis'] \
            - rps['valor_cofins'] \
            - rps['valor_inss'] \
            - rps['valor_ir'] \
            - rps['valor_csll'] \
            - rps['outras_retencoes'] \
            - rps['valor_iss_retido'] \
            - rps['desconto_incondicionado'] \
            - rps['desconto_condicionado']

        rps['codigo_servico'] = rps['itens_servico'][0]['codigo_servico']

        if rps['itens_servico'][0]['cnae_servico']:
            rps['cnae_servico'] = rps['itens_servico'][0]['cnae_servico']

        rps['descricao'] = rps['discriminacao']
        
        # Codigo do municipio do IBGE
        rps['codigo_municipio'] = rps['emissor']['codigo_municipio']
        
        rps['prestador'] = rps['emissor']

        rps['tomador']['logradouro'] = rps['tomador']['endereco']['logradouro']
        rps['tomador']['numero'] = rps['tomador']['endereco']['numero']
        rps['tomador']['complemento'] = rps['tomador']['endereco']['complemento']
        rps['tomador']['bairro'] = rps['tomador']['endereco']['bairro']
        rps['tomador']['cidade'] = rps['tomador']['endereco']['codigo_municipio']
        rps['tomador']['uf'] = rps['tomador']['endereco']['uf']
        rps['tomador']['cep'] = rps['tomador']['endereco']['cep']
        rps['tomador']['telefone'] = ''

        rps['valor_servico'] = "%.2f" % rps['valor_servico']


        # TODO: pegar da configuração, pois estão todos fixos

        # Código de tipo de RPS
        # 1 - RPS
        # 2 – Nota Fiscal Conjugada (Mista)
        # 3 – Cupom
        rps['tipo_rps'] = 1

        # Nota a ser substituida, mesmos tipos do numero, serie e tipo respectivamente
        # if rps['tipo_rps'] != 1:
        #     rps['numero_substituido'] = 
        #     rps['serie_substituido'] = 
        #     rps['tipo_substituido'] = 

        
        # Código de natureza da operação
        # 1 – Tributação no município
        # 2 - Tributação fora do município
        # 3 - Isenção
        # 4 - Imune
        # 5 –Exigibilidade suspensa por decisão judicial
        # 6 – Exigibilidade suspensa por procedimento
        # administrativo        
        rps['natureza_operacao'] = 1

        # Código de identificação do regime especial de
        # tributação
        # 1 – Microempresa municipal
        # 2 - Estimativa
        # 3 – Sociedade de profissionais
        # 4 – Cooperativa
        # 5 - Microempresário Individual (MEI)
        # 6 - Microempresário e Empresa de Pequeno Porte
        # (ME EPP)        
        rps['regime_tributacao'] = 6 
        
        rps['incentivador_cultural'] = 2 
        rps['status'] = 1

        rps['valor_deducao'] = ''
        rps['valor_pis'] = ''
        rps['valor_cofins'] = ''
        rps['valor_inss'] = ''
        rps['valor_ir'] = ''
        rps['valor_csll'] = ''
        rps['outras_retencoes'] = ''
        rps['desconto_incondicionado'] = ''
        rps['desconto_condicionado'] = ''

        # TODO: Validar construcao_civil e intermediario na NFS

    return result


def send_api(certificate, password, edocs):
    cert_pfx = base64.decodestring(certificate)
    certificado = Certificado(cert_pfx, password)

    nfse_values = _convert_values(edocs)
    resposta = recepcionar_lote_rps(certificado, nfse=nfse_values, ambiente=edocs[0]['ambiente'])

    retorno = resposta['object']

    _logger.error('resposta')
    _logger.error(resposta)
    _logger.error(retorno)

    if hasattr(retorno, 'NumeroLote'):
        if edocs[0]['ambiente'] == 'producao':
            return {
                'code': 'processing',
                'entity': {
                    'numero_nfe': retorno.NumeroLote,
                    'protocolo_nfe': retorno.Protocolo,
                },
                'xml': resposta['sent_xml'].encode('utf-8'),
            }
        else:
            return {
                'code': 'processing',
                'entity': {
                    'protocolo_nfe':  retorno.Protocolo,
                    'numero_nfe': retorno.NumeroLote,
                },
                'xml': resposta['sent_xml'].encode('utf-8'),
            }
    else:
        return {
            'code': 400,
            'api_code': retorno.ListaMensagemRetorno.MensagemRetorno.Codigo,
            'message': retorno.ListaMensagemRetorno.MensagemRetorno.Mensagem + ' ' + retorno.ListaMensagemRetorno.MensagemRetorno.Correcao,
        }


def cancel_api(certificate, password, vals):
    cert_pfx = base64.decodestring(certificate)
    certificado = Certificado(cert_pfx, password)
    
    _logger.error('cancel_api')
    _logger.error(vals)

    # Código de cancelamento com base na tabela de Erros e alertas
    # tsCodigoCancelamentoNfse C Código de cancelamento com base na tabela de
    # Erros e alertas.
    # 1 – Erro na emissão
    # 2 – Serviço não prestado
    # 3 – Erro de assinatura
    # 4 – Duplicidade da nota
    # 5 – Erro de processamento
    # Importante: Os códigos 3 (Erro de assinatura) e
    # 5 (Erro de processamento) são de uso restrito da
    # Administração Tributária Municipal 
    codigo_cancelamento = 1

    canc = {
        'numero_nfse': vals['numero'],
        'cnpj_prestador':  "%014s" % vals['cnpj_cpf'],
        'inscricao_municipal': vals['inscricao_municipal'],
        'cidade': vals['codigo_municipio'],
        'codigo_cancelamento': "%04d" % codigo_cancelamento,
        # 'codigo_cancelamento': codigo_cancelamento,
    }
    resposta = cancelar_nfse(certificado, cancelamento=canc, ambiente=vals['ambiente'])
    retorno = resposta['object']

    _logger.error('resultado')
    _logger.error(resposta)

    if hasattr(retorno, 'ListaMensagemRetorno'):
        return {
            'code': 400,
            'api_code': retorno.ListaMensagemRetorno.MensagemRetorno.Codigo,
            'message': retorno.ListaMensagemRetorno.MensagemRetorno.Mensagem + ' ' + retorno.ListaMensagemRetorno.MensagemRetorno.Correcao,
        }
    else:
        if vals['ambiente'] == 'producao':
            return {
                'code': 201,
                'entity': {
                    'numero_nfe': retorno.NumeroLote,
                    'protocolo_nfe': retorno.Protocolo,
                },
                'xml': resposta['sent_xml'].encode('utf-8'),
            }
        else:
            return {
                'code': 201,
                'entity': {
                    'protocolo_nfe':  "homologacao: {}".format(retorno.Protocolo),
                    'numero_nfe': retorno.NumeroLote,
                },
                'xml': resposta['sent_xml'].encode('utf-8'),
            }

def check_nfse_api(certificate, password, edocs):
    _logger.info('check_nfse_api')
    _logger.info(edocs)
   
    cert_pfx = base64.decodestring(certificate)
    certificado = Certificado(cert_pfx, password)

    return _consultar_situacao_lote(certificado, consulta=edocs, ambiente=edocs['ambiente'])
    

def _consultar_situacao_lote(certificado, **kwargs):
    _logger.info('_consultar_situacao_lote')
    resposta = consultar_situacao_lote(certificado, **kwargs)
    retorno = resposta['object']

    _logger.info('_consultar_situacao_lote.resultado')
    _logger.info(resposta)

    if hasattr(retorno, 'ListaMensagemRetorno'):
        return {
            'code': 400,
            'final': False,
            'api_code': retorno.ListaMensagemRetorno.MensagemRetorno.Codigo,
            'message': retorno.ListaMensagemRetorno.MensagemRetorno.Mensagem + ' ' + retorno.ListaMensagemRetorno.MensagemRetorno.Correcao,
        }
    else:
        # Código de situação de lote de RPS
        # 1 – Não Recebido
        # 2 – Não Processado
        # 3 – Processado com Erro
        # 4 – Processado com Sucesso
        if retorno.Situacao == 1:
            return {
                'code': 400,
                'final': False,
                'api_code': retorno.Situacao,
                'message': 'Não Recebido',
            }
        elif retorno.Situacao == 2:
            return {
                'code': 400,
                'final': False,
                'api_code': retorno.Situacao,
                'message': 'Não Processado',
            }
        else:
            return _consultar_lote_rps(certificado, **kwargs)
            # return {
            #     'code': 400,
            #     'final': False,
            #     'api_code': '666',
            #     'message': 'Erro não identificado',
            #     'final': False
            # }


def _consultar_lote_rps(certificado, **kwargs):
    _logger.info('_consultar_lote_rps')
    resposta = consultar_lote_rps(certificado, **kwargs)
    retorno = resposta['object']

    _logger.info('_consultar_lote_rps.resultado')
    _logger.info(resposta)

    if hasattr(retorno, 'ListaMensagemRetorno'):
        return {
            'code': 400,
            'final': True,
            'api_code': retorno.ListaMensagemRetorno.MensagemRetorno.Codigo,
            'message': retorno.ListaMensagemRetorno.MensagemRetorno.Mensagem + ' ' + retorno.ListaMensagemRetorno.MensagemRetorno.Correcao,
        }
    else:
        return {
            'code': 400,
            'final': False,
            'api_code': '666',
            'message': 'Erro não identificado',
        }
