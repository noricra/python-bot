"""
Service de génération de graphiques professionnels
Utilise QuickChart API pour générer des images Chart.js
"""

import urllib.parse
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ChartService:
    """Service pour générer des graphiques via QuickChart API"""

    QUICKCHART_URL = "https://quickchart.io/chart"

    def __init__(self):
        self.base_url = self.QUICKCHART_URL

    def generate_revenue_chart(
        self,
        dates: List[str],
        revenues: List[float],
        width: int = 600,
        height: int = 400
    ) -> str:
        """
        Génère un graphique de revenus (line chart)

        Args:
            dates: Liste de dates (format 'YYYY-MM-DD')
            revenues: Liste de revenus correspondants
            width: Largeur image (px)
            height: Hauteur image (px)

        Returns:
            URL de l'image du graphique
        """
        chart_config = {
            "type": "line",
            "data": {
                "labels": dates,
                "datasets": [{
                    "label": "Revenus (USD)",
                    "data": revenues,
                    "borderColor": "rgb(75, 192, 192)",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "fill": True,
                    "tension": 0.4
                }]
            },
            "options": {
                "title": {
                    "display": True,
                    "text": "Revenus (30 derniers jours)",
                    "fontSize": 16
                },
                "scales": {
                    "yAxes": [{
                        "ticks": {
                            "beginAtZero": True
                        }
                    }]
                },
                "legend": {
                    "display": True
                }
            }
        }

        return self._build_chart_url(chart_config, width, height)

    def generate_sales_chart(
        self,
        dates: List[str],
        sales: List[int],
        width: int = 600,
        height: int = 400
    ) -> str:
        """
        Génère un graphique de ventes (bar chart)

        Args:
            dates: Liste de dates
            sales: Liste de ventes correspondantes
            width: Largeur image
            height: Hauteur image

        Returns:
            URL de l'image du graphique
        """
        chart_config = {
            "type": "bar",
            "data": {
                "labels": dates,
                "datasets": [{
                    "label": "Ventes",
                    "data": sales,
                    "backgroundColor": "rgba(54, 162, 235, 0.5)",
                    "borderColor": "rgb(54, 162, 235)",
                    "borderWidth": 1
                }]
            },
            "options": {
                "title": {
                    "display": True,
                    "text": "Ventes (30 derniers jours)",
                    "fontSize": 16
                },
                "scales": {
                    "yAxes": [{
                        "ticks": {
                            "beginAtZero": True,
                            "stepSize": 1
                        }
                    }]
                }
            }
        }

        return self._build_chart_url(chart_config, width, height)

    def generate_product_performance_chart(
        self,
        product_titles: List[str],
        sales_counts: List[int],
        revenues: List[float],
        width: int = 700,
        height: int = 400
    ) -> str:
        """
        Génère un graphique comparatif des performances produits (mixed chart)

        Args:
            product_titles: Titres des produits (max 10)
            sales_counts: Nombre de ventes par produit
            revenues: Revenus par produit
            width: Largeur image
            height: Hauteur image

        Returns:
            URL de l'image du graphique
        """
        # Limiter à 10 produits
        if len(product_titles) > 10:
            product_titles = product_titles[:10]
            sales_counts = sales_counts[:10]
            revenues = revenues[:10]

        chart_config = {
            "type": "bar",
            "data": {
                "labels": product_titles,
                "datasets": [
                    {
                        "label": "Ventes",
                        "data": sales_counts,
                        "backgroundColor": "rgba(255, 99, 132, 0.5)",
                        "borderColor": "rgb(255, 99, 132)",
                        "borderWidth": 1,
                        "yAxisID": "y-axis-1"
                    },
                    {
                        "label": "Revenus (USD)",
                        "data": revenues,
                        "backgroundColor": "rgba(75, 192, 192, 0.5)",
                        "borderColor": "rgb(75, 192, 192)",
                        "borderWidth": 1,
                        "yAxisID": "y-axis-2"
                    }
                ]
            },
            "options": {
                "title": {
                    "display": True,
                    "text": "Performance par Produit",
                    "fontSize": 16
                },
                "scales": {
                    "yAxes": [
                        {
                            "id": "y-axis-1",
                            "type": "linear",
                            "position": "left",
                            "ticks": {
                                "beginAtZero": True,
                                "stepSize": 1
                            },
                            "scaleLabel": {
                                "display": True,
                                "labelString": "Ventes"
                            }
                        },
                        {
                            "id": "y-axis-2",
                            "type": "linear",
                            "position": "right",
                            "ticks": {
                                "beginAtZero": True
                            },
                            "scaleLabel": {
                                "display": True,
                                "labelString": "Revenus (USD)"
                            },
                            "gridLines": {
                                "drawOnChartArea": False
                            }
                        }
                    ]
                }
            }
        }

        return self._build_chart_url(chart_config, width, height)

    def generate_category_distribution_chart(
        self,
        categories: List[str],
        sales: List[int],
        width: int = 500,
        height: int = 500
    ) -> str:
        """
        Génère un pie chart de distribution par catégorie

        Args:
            categories: Noms des catégories
            sales: Nombre de ventes par catégorie
            width: Largeur image
            height: Hauteur image

        Returns:
            URL de l'image du graphique
        """
        colors = [
            "rgba(255, 99, 132, 0.8)",
            "rgba(54, 162, 235, 0.8)",
            "rgba(255, 206, 86, 0.8)",
            "rgba(75, 192, 192, 0.8)",
            "rgba(153, 102, 255, 0.8)",
            "rgba(255, 159, 64, 0.8)",
            "rgba(199, 199, 199, 0.8)"
        ]

        chart_config = {
            "type": "pie",
            "data": {
                "labels": categories,
                "datasets": [{
                    "data": sales,
                    "backgroundColor": colors[:len(categories)]
                }]
            },
            "options": {
                "title": {
                    "display": True,
                    "text": "Ventes par Catégorie",
                    "fontSize": 16
                },
                "legend": {
                    "display": True,
                    "position": "right"
                }
            }
        }

        return self._build_chart_url(chart_config, width, height)

    def generate_combined_dashboard_chart(
        self,
        dates: List[str],
        revenues: List[float],
        sales: List[int],
        width: int = 800,
        height: int = 400
    ) -> str:
        """
        Génère un graphique combiné revenus + ventes

        Args:
            dates: Liste de dates
            revenues: Revenus par jour
            sales: Ventes par jour
            width: Largeur image
            height: Hauteur image

        Returns:
            URL de l'image du graphique
        """
        chart_config = {
            "type": "line",
            "data": {
                "labels": dates,
                "datasets": [
                    {
                        "label": "Revenus (USD)",
                        "data": revenues,
                        "borderColor": "rgb(75, 192, 192)",
                        "backgroundColor": "rgba(75, 192, 192, 0.2)",
                        "fill": True,
                        "yAxisID": "y-axis-1",
                        "tension": 0.4
                    },
                    {
                        "label": "Ventes",
                        "data": sales,
                        "borderColor": "rgb(255, 99, 132)",
                        "backgroundColor": "rgba(255, 99, 132, 0.2)",
                        "fill": False,
                        "yAxisID": "y-axis-2",
                        "tension": 0.4
                    }
                ]
            },
            "options": {
                "title": {
                    "display": True,
                    "text": "Revenus & Ventes - Évolution",
                    "fontSize": 18
                },
                "scales": {
                    "yAxes": [
                        {
                            "id": "y-axis-1",
                            "type": "linear",
                            "position": "left",
                            "ticks": {
                                "beginAtZero": True
                            },
                            "scaleLabel": {
                                "display": True,
                                "labelString": "Revenus (USD)"
                            }
                        },
                        {
                            "id": "y-axis-2",
                            "type": "linear",
                            "position": "right",
                            "ticks": {
                                "beginAtZero": True,
                                "stepSize": 1
                            },
                            "scaleLabel": {
                                "display": True,
                                "labelString": "Ventes"
                            },
                            "gridLines": {
                                "drawOnChartArea": False
                            }
                        }
                    ]
                },
                "legend": {
                    "display": True,
                    "position": "top"
                }
            }
        }

        return self._build_chart_url(chart_config, width, height)

    def _build_chart_url(self, chart_config: Dict, width: int, height: int) -> str:
        """
        Construit l'URL QuickChart avec la configuration

        Retourne maintenant un tuple (url, json_data) pour utiliser POST
        au lieu de GET, car GET ne supporte pas les fonctions callback

        Args:
            chart_config: Configuration Chart.js
            width: Largeur
            height: Hauteur

        Returns:
            Tuple (url, json_data) pour requête POST
        """
        # Retourner URL de base + données pour POST
        # Format: on retourne juste l'URL, mais le handler devra faire un POST
        # avec le JSON dans le body
        return self.base_url, {
            "chart": chart_config,
            "width": width,
            "height": height,
            "backgroundColor": "white"
        }

    def get_last_30_days_labels(self) -> List[str]:
        """
        Génère les labels pour les 30 derniers jours

        Returns:
            Liste de dates au format 'MM-DD'
        """
        today = datetime.now()
        dates = []

        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            dates.append(date.strftime('%m-%d'))

        return dates

    def get_last_7_days_labels(self) -> List[str]:
        """
        Génère les labels pour les 7 derniers jours

        Returns:
            Liste de dates au format 'MM-DD'
        """
        today = datetime.now()
        dates = []

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            dates.append(date.strftime('%m-%d'))

        return dates
