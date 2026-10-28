/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Alias "drug_search" → campo many2one estandar sobre cs.drug.catalog.
 *
 * La busqueda CIMA avanzada se realiza desde el menu CIMA → Catalogo.
 * Reutiliza el descriptor "many2one" ya registrado (robusto ante refactors del core Odoo).
 */
const fields = registry.category("fields");
fields.add("drug_search", fields.get("many2one"));
