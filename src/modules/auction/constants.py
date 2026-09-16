class AuctionStatus:
    PENDING = "pending" 
    LIVE = "live"
    SOLD = "sold"
    UNSOLD = "unsold"
    CANCELLED = "cancelled"


class AuctionLiveKeys:
    SESSION = "auction:session"
    CURRENT = "auction:current"
    STATUS = "auction:status"
    BID = "auction:bid"
    TIMER = "auction:timer"
    BIDDING_ENABLED = "auction:bidding_enabled"

    REMAINING_QUEUE = "auction:queue:remaining"
    UNSOLD_QUEUE = "auction:queue:unsold"


class AuctionCurrency:
    MAROON_PER_SAFFRON = 25
    SAFFRON_PER_PURPLE = 25
    MAROON_PER_PURPLE = 625

    TEAM_INITIAL_BALANCE = 6250



BID_LADDER = [
    5,
    10,
    15,
    20,
    25,
    50,
    75,
    100,
    125,
    175,
    225,
    275,
    325,
    425,
    525,
    625,
    750,
    875,
    1000,
    1150,
    1300,
    1450,
    1600,
    1800,
    2000,
    2500,
    3125,
    3750,
    4375,
    5000,
]


class AuctionSessionStatus:
    PENDING = "pending"
    LIVE = "live"
    PAUSED = "paused"
    ENDED = "ended"


class AuctionSortField:
    CURRENT_QUEUE = "current_queue"
    BASE_PRICE = "base_price"
    ROLL_NO = "roll_no"
    NAME = "name"
    CREATED_AT = "created_at"
    CUSTOM_CSV = "custom_csv"


class AuctionSortDirection:
    ASC = "asc"
    DESC = "desc"

