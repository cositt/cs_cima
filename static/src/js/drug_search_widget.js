/** @odoo-module **/

import { many2OneField } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";

/**
 * Alias "drug_search" → Many2OneField estándar sobre cs.drug.catalog.
 *
 * La búsqueda CIMA avanzada se realiza desde el menú CIMA → Catálogo.
 * Esto evita la necesidad de un template OWL personalizado y funciona
 * con el autocomplete estándar de Odoo.
 */
registry.category("fields").add("drug_search", many2OneField);
