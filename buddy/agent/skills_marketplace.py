"""
Buddy Skills Marketplace

A community-driven skill discovery and distribution system that enables
agents to publish, discover, rate, and install skills from the Buddy ecosystem.

The marketplace provides a catalog of verified skills across multiple domains,
with versioning, dependency management, and reputation scoring for publishers.
Agents can browse the marketplace, install skills directly, and contribute
their own skills for others to use.
"""

import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("buddy.marketplace")


class SkillCategory(str, Enum):
    """Categories for marketplace skills."""
    CODING = "coding"
    WRITING = "writing"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    DATA = "data"
    DESIGN = "design"
    COMMUNICATION = "communication"
    RESEARCH = "research"
    DEV_OPS = "dev_ops"
    FINANCE = "finance"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    UTILITY = "utility"


class SkillPricing(str, Enum):
    """Pricing models for marketplace skills."""
    FREE = "free"
    FREEMIUM = "freemium"
    PAID = "paid"
    SUBSCRIPTION = "subscription"
    ENTERPRISE = "enterprise"


class SkillReviewSentiment(str, Enum):
    """Review sentiment for marketplace skills."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class MarketplaceSkill:
    """A skill listing in the Buddy marketplace."""
    id: str
    name: str
    description: str
    category: SkillCategory
    version: str = "1.0.0"
    author: str = ""
    author_id: str = ""
    pricing: SkillPricing = SkillPricing.FREE
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    prompt_template: str = ""
    tool_requirements: list[str] = field(default_factory=list)
    icon_url: str = ""
    homepage: str = ""
    documentation_url: str = ""
    source_code_url: str = ""
    published_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    verified: bool = False
    min_platform_version: str = "1.0.0"


@dataclass
class SkillReview:
    """A user review for a marketplace skill."""
    id: str
    skill_id: str
    reviewer_id: str
    reviewer_name: str
    rating: float  # 1-5
    title: str = ""
    content: str = ""
    sentiment: SkillReviewSentiment = SkillReviewSentiment.NEUTRAL
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    helpful_count: int = 0


@dataclass
class PublisherProfile:
    """Profile of a skill publisher on the marketplace."""
    id: str
    name: str
    bio: str = ""
    website: str = ""
    github: str = ""
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_skills: int = 0
    total_downloads: int = 0
    average_rating: float = 0.0
    verified: bool = False


class SkillsMarketplace:
    """Skills marketplace for the Buddy platform.

    Manages the complete lifecycle of community-contributed skills:
    - Skill publication with versioning and metadata
    - Browse and discovery with category filtering and search
    - Rating and review system with reputation tracking
    - Verified skill curation
    - Publisher profiles and reputation
    """

    def __init__(self):
        self._skills: dict[str, MarketplaceSkill] = {}
        self._reviews: dict[str, list[SkillReview]] = {}
        self._publishers: dict[str, PublisherProfile] = {}
        self._featured_skills: list[str] = []
        self._verified_skills: set[str] = set()
        logger.info("Skills Marketplace initialized")

    def publish_skill(self, skill: MarketplaceSkill) -> MarketplaceSkill:
        """Publish a new skill to the marketplace."""
        skill_id = hashlib.md5(
            f"{skill.name}:{skill.author}:{skill.version}".encode()
        ).hexdigest()[:12]
        skill.id = skill_id
        skill.published_at = datetime.now(timezone.utc).isoformat()
        skill.updated_at = skill.published_at

        self._skills[skill_id] = skill
        self._reviews[skill_id] = []

        # Update publisher profile
        pub = self._get_or_create_publisher(skill.author_id, skill.author)
        pub.total_skills += 1

        logger.info(f"Skill published: {skill.name} v{skill.version} by {skill.author}")
        return skill

    def update_skill(self, skill_id: str, updates: dict) -> Optional[MarketplaceSkill]:
        """Update an existing skill listing."""
        if skill_id not in self._skills:
            return None

        skill = self._skills[skill_id]
        for key, value in updates.items():
            if hasattr(skill, key):
                setattr(skill, key, value)

        skill.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Skill updated: {skill.name}")
        return skill

    def get_skill(self, skill_id: str) -> Optional[MarketplaceSkill]:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def search_skills(
        self,
        query: str = "",
        category: Optional[SkillCategory] = None,
        tags: list[str] = None,
        pricing: Optional[SkillPricing] = None,
        sort_by: str = "rating",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search and filter marketplace skills."""
        results = list(self._skills.values())

        if query:
            q = query.lower()
            results = [
                s for s in results
                if q in s.name.lower()
                or q in s.description.lower()
                or any(q in tag.lower() for tag in s.tags)
            ]

        if category:
            results = [s for s in results if s.category == category]

        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]

        if pricing:
            results = [s for s in results if s.pricing == pricing]

        # Sort
        if sort_by == "rating":
            results.sort(key=lambda s: (s.rating, s.downloads), reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda s: s.downloads, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda s: s.published_at, reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda s: s.name.lower())

        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "items": [self._skill_to_dict(s) for s in results[start:end]],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def add_review(self, review: SkillReview) -> SkillReview:
        """Add a review for a skill."""
        if review.skill_id not in self._skills:
            raise ValueError(f"Skill {review.skill_id} not found")

        review.id = hashlib.md5(
            f"{review.skill_id}:{review.reviewer_id}:{review.created_at}".encode()
        ).hexdigest()[:12]

        self._reviews[review.skill_id].append(review)

        # Update skill rating
        skill = self._skills[review.skill_id]
        all_reviews = self._reviews[review.skill_id]
        skill.rating = sum(r.rating for r in all_reviews) / len(all_reviews)
        skill.rating_count = len(all_reviews)

        # Update publisher rating
        pub = self._publishers.get(skill.author_id)
        if pub:
            pub_skills = [s for s in self._skills.values() if s.author_id == skill.author_id]
            if pub_skills:
                pub.average_rating = sum(s.rating for s in pub_skills) / len(pub_skills)

        logger.info(f"Review added for skill {skill.name}: {review.rating}/5")
        return review

    def get_reviews(
        self, skill_id: str, page: int = 1, page_size: int = 20
    ) -> dict:
        """Get reviews for a skill."""
        reviews = self._reviews.get(skill_id, [])
        total = len(reviews)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "items": [
                {
                    "id": r.id,
                    "reviewer_name": r.reviewer_name,
                    "rating": r.rating,
                    "title": r.title,
                    "content": r.content,
                    "sentiment": r.sentiment.value,
                    "created_at": r.created_at,
                    "helpful_count": r.helpful_count,
                }
                for r in reviews[start:end]
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "average_rating": sum(r.rating for r in reviews) / max(len(reviews), 1),
        }

    def record_download(self, skill_id: str):
        """Record a download of a skill."""
        if skill_id in self._skills:
            self._skills[skill_id].downloads += 1
            pub = self._publishers.get(self._skills[skill_id].author_id)
            if pub:
                pub.total_downloads += 1

    def verify_skill(self, skill_id: str):
        """Mark a skill as verified."""
        if skill_id in self._skills:
            self._skills[skill_id].verified = True
            self._verified_skills.add(skill_id)
            logger.info(f"Skill verified: {self._skills[skill_id].name}")

    def feature_skill(self, skill_id: str):
        """Feature a skill on the marketplace homepage."""
        if skill_id in self._skills and skill_id not in self._featured_skills:
            self._featured_skills.append(skill_id)
            if len(self._featured_skills) > 10:
                self._featured_skills = self._featured_skills[-10:]
            logger.info(f"Skill featured: {self._skills[skill_id].name}")

    def get_featured_skills(self) -> list[dict]:
        """Get featured skills for the marketplace homepage."""
        return [
            self._skill_to_dict(self._skills[sid])
            for sid in self._featured_skills
            if sid in self._skills
        ]

    def get_categories(self) -> list[dict]:
        """Get category statistics."""
        category_counts = {}
        for skill in self._skills.values():
            cat = skill.category.value
            if cat not in category_counts:
                category_counts[cat] = {"count": 0, "avg_rating": 0.0}
            category_counts[cat]["count"] += 1

        # Calculate averages
        for cat, data in category_counts.items():
            skills = [s for s in self._skills.values() if s.category.value == cat]
            if skills:
                data["avg_rating"] = round(
                    sum(s.rating for s in skills) / len(skills), 2
                )

        return [
            {"category": cat, **data}
            for cat, data in sorted(category_counts.items(), key=lambda x: x[1]["count"], reverse=True)
        ]

    def get_publisher(self, publisher_id: str) -> Optional[dict]:
        """Get a publisher profile."""
        pub = self._publishers.get(publisher_id)
        if not pub:
            return None

        skills = [
            self._skill_to_dict(s)
            for s in self._skills.values()
            if s.author_id == publisher_id
        ]

        return {
            "id": pub.id,
            "name": pub.name,
            "bio": pub.bio,
            "website": pub.website,
            "github": pub.github,
            "joined_at": pub.joined_at,
            "total_skills": pub.total_skills,
            "total_downloads": pub.total_downloads,
            "average_rating": round(pub.average_rating, 2),
            "verified": pub.verified,
            "skills": skills,
        }

    def get_stats(self) -> dict:
        """Get marketplace statistics."""
        return {
            "total_skills": len(self._skills),
            "total_reviews": sum(len(r) for r in self._reviews.values()),
            "total_publishers": len(self._publishers),
            "total_downloads": sum(s.downloads for s in self._skills.values()),
            "verified_skills": len(self._verified_skills),
            "featured_skills": len(self._featured_skills),
            "categories": self.get_categories(),
            "top_rated": [
                self._skill_to_dict(s)
                for s in sorted(
                    self._skills.values(),
                    key=lambda s: (s.rating, s.downloads),
                    reverse=True,
                )[:5]
            ],
            "most_downloaded": [
                self._skill_to_dict(s)
                for s in sorted(
                    self._skills.values(),
                    key=lambda s: s.downloads,
                    reverse=True,
                )[:5]
            ],
        }

    def _skill_to_dict(self, skill: MarketplaceSkill) -> dict:
        """Convert a skill to a dictionary for API responses."""
        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "category": skill.category.value,
            "version": skill.version,
            "author": skill.author,
            "author_id": skill.author_id,
            "pricing": skill.pricing.value,
            "tags": skill.tags,
            "dependencies": skill.dependencies,
            "tool_requirements": skill.tool_requirements,
            "icon_url": skill.icon_url,
            "homepage": skill.homepage,
            "documentation_url": skill.documentation_url,
            "published_at": skill.published_at,
            "updated_at": skill.updated_at,
            "downloads": skill.downloads,
            "rating": round(skill.rating, 2),
            "rating_count": skill.rating_count,
            "verified": skill.verified,
        }

    def _get_or_create_publisher(self, publisher_id: str, name: str) -> PublisherProfile:
        """Get or create a publisher profile."""
        if publisher_id not in self._publishers:
            self._publishers[publisher_id] = PublisherProfile(
                id=publisher_id,
                name=name,
            )
        return self._publishers[publisher_id]


# Global singleton
skills_marketplace = SkillsMarketplace()