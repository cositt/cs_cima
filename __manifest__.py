{
    'name': 'Centro Sanitario - CIMA',
    'version': '19.0.2.1.0',
    'category': 'Healthcare',
    'author': 'Equilibrium',
    'license': 'LGPL-3',
    'summary': 'Catálogo de medicamentos integrado con CIMA (AEMPS) — gratuito, sin API key',
    'depends': ['base', 'mail', 'account', 'cs_resident', 'cs_medical_care'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'wizards/cima_import_wizard_views.xml',
        'views/cs_drug_usage_log_views.xml',
        'views/cs_drug_catalog_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
        'views/prescription_cima_views.xml',
        'views/medical_care_cima_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cs_cima/static/src/js/drug_search_widget.js',
        ],
    },
    'installable': True,
    'application': True,
}
