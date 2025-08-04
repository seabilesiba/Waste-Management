{
    "name": "Waste Management",
    "version": "1.0",
    "depends": ["base","mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/pickup_point_views.xml",
        "views/waste_container.xml",
        "views/request_waste_service.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True
}
