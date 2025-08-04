from odoo import models, fields, api


class WasteServiceRequest(models.Model):
    _name = 'waste.service.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Waste Service Request'

    name = fields.Char(
        string='Request ID',
        required=True,
        # copy=False,
        readonly=True,
        default='New')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('waste.service.request') or 'New'
        return super().create(vals)

    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    pickup_point_id = fields.Many2one('pickup.point', string="Drop-off/Pickup Point", domain="[('partner_id', '=', partner_id)]")
    container_id = fields.Many2one('waste.container', string='Container')
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='pickup_point_id.partner_id',
        store=True,
        readonly=True
    )

    pickup_id = fields.Char(string="Pickup Point Name", related='pickup_point_id.name',)
    # Common
    service_type = fields.Selection([
        ('removal', 'Removal'),
        ('swap', 'Swap'),
        ('shunt', 'Shunt'),
        ('placement', 'Placement'),
        ('collection', 'Collection & Disposal'),
    ], string="Service Type", required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    container_type = fields.Selection([
        ('bin', 'Bin'),
        ('tank', 'Tank')
    ], String="container Type", default=''
    )


    inUse = fields.Boolean(string='InUse', related='container_id.inUse', defauld=True)
    # unUse = fields.Boolean(string='InUse', related='container_id.inUse', defauld=False)

    # Placement & Collection
    dropoff_container_ids = fields.Many2many('waste.container', 'waste_service_request_containers_rel', string="Containers")
    tank_ids = fields.Many2many('waste.container','waste_service_request_tanks_rel', string="Tanks")

    # # Swap
    # lifted_bin_id = fields.Many2one('waste.container', string="Old Bin (Lifted)")
    # dropped_bin_id = fields.Many2one('waste.container', string="New Bin (Dropped)")
    #
    # # Shunt
    # shunted_bin_id = fields.Many2one('waste.container', string="Bin to Shunt")
    shunt_from_id = fields.Many2one('pickup.point', string="From Location", domain="[('partner_id', '=', partner_id)]" )
    shunt_to_id = fields.Many2one('pickup.point', string="To Location", domain="[('partner_id', '=', partner_id)]" )

    lifted_bin_ids = fields.Many2many(
        'waste.container',
        'waste_service_request_lifted_rel',  # Different relation table
        'request_id',
        'container_id',
        string="Lifted Bins"
    )

    # lifted_bin_ids = fields.Many2many(
    #     'waste.container',
    #     # 'lifted_service_id',
    #     string="Old Bins (Lifted)"
    # )

    dropped_bin_ids = fields.Many2many(
        'waste.container',
        'waste_service_request_dropped_rel',  # Different relation table
        'request_id',
        'container_id',
        string="New Bins (Dropped)"
    )

    # Shunt
    shunted_bin_ids = fields.Many2many(
        'waste.container',
        'waste_service_request_shunted_rel',  # Different relation table
        'request_id',
        'container_id',
        string="Bins to Shunt"
    )
    condition = fields.Selection([
        ('draft', 'draft'),
        ('done', 'Done')],
        string='Condition', default='draft')
    tank_volume = fields.Selection([
        ('7000L', '7000 Liters'),
        ('9000L', '9000 Liters'),
        ('11000L', '11000 Liters'),
        ('12000L', '12000 Liters'),
        ('15000L', '15000 Liters'),
    ], default='', string='Tank Volume',related='tank_ids.tank_volume'
    )

    liters_collected = fields.Float(string="Liters Collected",)
    liters_remaining = fields.Float(string="Liters Remaining", compute="_compute_liters_remaining", store=True)

    @api.depends('liters_collected', 'tank_volume')
    def _compute_liters_remaining(self):
        for rec in self:
            try:
                total = float(rec.tank_volume.replace('L', '')) if rec.tank_volume else 0
            except:
                total = 0
            rec.liters_remaining = max(0.0, total - rec.liters_collected)

    def action_draft(self):
        self.condition = 'draft'

    def action_mark_done(self):
        for record in self:
            if record.service_type == 'removal':
                for container in record.dropoff_container_ids:
                    container.pickup_point_id = False
                    container.customer_id = False
                    container.inUse = False
                    container.status = 'un_use'
                    record.message_post(body=f"Removed bin: {container.name}")

            elif record.service_type == 'swap':
                for lifted_bin in record.lifted_bin_ids:
                    lifted_bin.pickup_point_id = False
                    lifted_bin.customer_id = False
                    lifted_bin.inUse = False
                    lifted_bin.status = 'un_use'
                    record.message_post(body=f"Lifted bin '{lifted_bin.name}' from '{record.pickup_point_id.name}'")

                for dropped_bin in record.dropped_bin_ids:
                    dropped_bin.pickup_point_id = record.pickup_point_id
                    dropped_bin.customer_id = record.customer_id
                    dropped_bin.inUse = True
                    dropped_bin.status = 'in_use'
                    record.message_post(body=f"Dropped bin '{dropped_bin.name}' at '{record.pickup_point_id.name}'")

            elif record.service_type == 'shunt':
                for bin in record.shunted_bin_ids:
                    bin.pickup_point_id = record.shunt_to_id
                    bin.inUse = True
                    bin.status = 'in_use'
                    record.message_post(
                        body=f"Shunted bin '{bin.name}' from '{record.shunt_from_id.name}' to '{record.shunt_to_id.name}'")

            elif record.service_type == 'placement':
                for container in record.dropoff_container_ids:
                    container.pickup_point_id = record.pickup_point_id
                    container.customer_id = record.customer_id
                    container.inUse = True
                    container.status = 'in_use'
                    record.message_post(body=f"Placed bin: {container.name} at {record.pickup_point_id.name}")

            elif record.service_type == 'collection':
                for container in record.dropoff_container_ids:
                    container.pickup_point_id = False
                    container.customer_id = False
                    container.inUse = False
                    container.status = 'un_use'
                    record.message_post(body=f"Collected & Disposed bin: {container.name}")

                for tank in record.tank_ids.filtered(lambda c: c.container_type == 'tank'):
                    tank.pickup_point_id = record.pickup_point_id
                    tank.customer_id = record.customer_id
                    tank.inUse = True
                    tank.status = 'in_use'
                    record.message_post(body=f"Collected & Emptied tank: {tank.name} ({tank.tank_volume})")

                    if record.service_type == 'collection' and record.container_type == 'tank':
                        record.tank_ids.write({
                            'liters_collected': record.liters_collected,
                            'liters_remaining': record.liters_remaining,
                        })

        self.condition = 'done'






