# -*- coding: utf-8 -*-
{
    "name": "Viáticos - Control y Validaciones",
    "version": "18.0.0.0.0",
    "category": "Human Resources",
    "summary": "Control de viáticos con importes permitidos, validaciones y reportes",
    "description": """
Módulo para la gestión de viáticos:
- Configuración de importes máximos por rubro
- Control de solicitudes y aprobaciones
- Validaciones por cargo, fechas y montos
- Base para preliquidación y liquidación de viáticos
""",
    "author": "PentaLab",
    "contributors": [
        "Sebastian Bedoya <sbedoya@pentalab.tech>",
    ],
    "website": "https://pentalab.tech/",
    "license": "LGPL-3",
    "depends": [
        "product",
        "hr",
        "hr_expense",
        "approvals",
        "pentalab_parish",
        "report_xlsx",
    ],
    "data": [
        "views/product_views.xml",
        "views/approval_category_views.xml",
        "views/approval_request_views.xml",
        "report/viaticos_report_actions.xml",
        "report/viaticos_report_templates.xml",
    ],
    "installable": True,
    "application": False,
}
