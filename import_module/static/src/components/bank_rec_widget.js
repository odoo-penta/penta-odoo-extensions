/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban";

patch(BankRecKanbanController.prototype, {
    getOne2ManyColumns() {
        const columns = super.getOne2ManyColumns(...arguments);
        const records = this.state.bankRecRecordData.line_ids.records;

        if (records.some(r => r.data.id_import)) {
            const debitIndex = columns.findIndex(col => col[0] === "debit");
            columns.splice(debitIndex, 0, ["id_import", _t("Guía Importación")]);
        }
        return columns;
    }
});
