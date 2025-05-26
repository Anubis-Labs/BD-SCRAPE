# Project Categorization Schema for Equinox Engineering

This document outlines a hierarchical schema for categorizing engineering, procurement, and construction management (EPCM) projects undertaken by Equinox Engineering. The goal is to provide a structured way to classify projects for easier searching, analysis, and association with specific expertise.

## Level 1: Primary Sector

### 1. Energy

#### 1.1. Oil & Gas
    *   **1.1.1. Upstream:**
        *   Well Sites & Gathering Systems
        *   Field Facilities
    *   **1.1.2. Midstream:**
        *   Gas Processing Plants (Sweetening, Dehydration, NGL Recovery, LNG, LPG, CNG)
        *   Compressor Stations
        *   Pump Stations
        *   Pipeline Systems (Gas, Oil, NGLs, Water)
        *   Storage Facilities (Tank Farms, Underground Storage)
        *   Metering Stations
    *   **1.1.3. Downstream (Support & Specialized):**
        *   Refinery Unit Revamps/Modifications (less common for pure EPCM, but possible)
        *   Petrochemical Interface Projects

#### 1.2. Conventional Power Generation
    *   **1.2.1. Gas-Fired Power Plants:**
        *   Simple Cycle
        *   Combined Cycle
    *   **1.2.2. Cogeneration / Combined Heat and Power (CHP)**
    *   **1.2.3. Waste Heat to Power**

### 2. Renewable & Sustainable Energy

#### 2.1. Solar Energy
    *   **2.1.1. Utility-Scale Solar Farms**
    *   **2.1.2. Commercial & Industrial Solar Installations**
    *   **2.1.3. Solar with Battery Energy Storage Systems (BESS)**

#### 2.2. Wind Energy
    *   **2.2.1. Onshore Wind Farms**
    *   **2.2.2. Wind Farm Substations & Grid Interconnection**

#### 2.3. Bioenergy
    *   **2.3.1. Biofuels Production Facilities (e.g., Ethanol, Biodiesel)**
    *   **2.3.2. Biomass-to-Power Plants**
    *   **2.3.3. Renewable Natural Gas (RNG) / Biomethane Plants**

#### 2.4. Geothermal Energy
    *   **2.4.1. Geothermal Power Plants**
    *   **2.4.2. Direct Use Geothermal Systems**

#### 2.5. Hydrogen
    *   **2.5.1. Green Hydrogen Production (Electrolysis)**
    *   **2.5.2. Blue Hydrogen Production (Steam Methane Reforming with CCUS)**
    *   **2.5.3. Hydrogen Storage & Transportation Infrastructure**

#### 2.6. Carbon Capture, Utilization, and Storage (CCUS)
    *   **2.6.1. Carbon Capture Units (Pre-combustion, Post-combustion, Oxy-combustion)**
    *   **2.6.2. CO2 Compression and Dehydration**
    *   **2.6.3. CO2 Pipelines**
    *   **2.6.4. CO2 Injection and Storage Facilities**

### 3. Specialized Infrastructure

#### 3.1. Data Centers
    *   **3.1.1. Hyperscale Data Centers**
    *   **3.1.2. Colocation Facilities**
    *   **3.1.3. Edge Data Centers**
    *   **3.1.4. Mission Critical Power & Cooling Systems**

#### 3.2. Water & Wastewater Management
    *   **3.2.1. Industrial Water Treatment Plants**
    *   **3.2.2. Produced Water Treatment & Disposal (Oil & Gas specific)**
    *   **3.2.3. Desalination Plants (if applicable)**

### 4. Other Industrial Projects
    *(This category can be used for projects that don't neatly fit above, or for specific niche industrial plant types Equinox might handle, e.g., mining & minerals processing support facilities, manufacturing plant utilities, etc.)*

    *   **4.1. Mining and Minerals Processing (Supporting Infrastructure)**
    *   **4.2. Manufacturing Facility Utilities & Infrastructure**


## Level 2: Project Phase / Service Type (Can apply across sectors)

*   Feasibility Studies & Conceptual Design
*   Front-End Engineering Design (FEED)
*   Detailed Engineering & Design
*   Procurement Services
*   Construction Management
*   Commissioning & Start-up Support
*   Project Management Consulting (PMC)
*   Debottlenecking & Optimization Studies
*   Revamp & Brownfield Modification Projects

## Level 3: Specific Equipment / Unit / Technology Focus (Examples)

This level would be highly variable and project-specific. It's intended to tag projects with key technologies or equipment involved.

*   **Example for Compressor Station (1.1.2):**
    *   Reciprocating Compressors
    *   Centrifugal Compressors
    *   Gas Turbines
    *   Dehydration Units (TEG)
    *   Station Control Systems
*   **Example for Gas Plant (1.1.2):**
    *   Amine Sweetening Unit
    *   Cryogenic NGL Recovery Unit
    *   Sulfur Recovery Unit (SRU)
    *   Fractionation Train
*   **Example for Solar Farm (2.1.1):**
    *   PV Modules (Monocrystalline, Polycrystalline, Thin-film)
    *   Inverters (Central, String)
    *   Tracking Systems (Fixed-tilt, Single-axis, Dual-axis)
    *   Substation and Interconnection
*   **Example for Data Center (3.1.x):**
    *   UPS Systems
    *   Chillers / CRAC / CRAH Units
    *   Power Distribution Units (PDUs)
    *   Backup Generators

---

**Notes:**

*   This schema is intended to be flexible and can be expanded as new project types or areas of expertise emerge.
*   A single project might be tagged with multiple categories, especially across Level 2 and Level 3.
*   The numbering system is for clarity; the actual implementation in a database might use foreign keys or a tag-based system for more flexibility.
*   The "Level 3" examples are illustrative; a more comprehensive list would be developed based on actual project data. 