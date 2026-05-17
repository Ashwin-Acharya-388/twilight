-- CreateEnum
CREATE TYPE "Gender" AS ENUM ('MALE', 'FEMALE', 'OTHER');

-- CreateEnum
CREATE TYPE "PlanType" AS ENUM ('INDIVIDUAL', 'FAMILY', 'SENIOR', 'GROUP', 'OTHER');

-- CreateTable
CREATE TABLE "User" (
    "id" SERIAL NOT NULL,
    "email" TEXT NOT NULL,
    "passwordHash" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "lastLogin" TIMESTAMP(3),

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Profile" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "fullName" TEXT,
    "age" INTEGER,
    "gender" "Gender",
    "bmi" DOUBLE PRECISION,
    "heightCm" DOUBLE PRECISION,
    "weightKg" DOUBLE PRECISION,
    "occupation" TEXT,
    "city" TEXT,
    "annualIncome" DOUBLE PRECISION,
    "smoker" BOOLEAN,
    "alcoholUse" BOOLEAN,
    "exerciseFrequency" TEXT,
    "familyHistory" TEXT,
    "preExistingConditions" JSONB,
    "maritalStatus" TEXT,
    "dependents" INTEGER,
    "lifestyleNotes" TEXT,

    CONSTRAINT "Profile_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ExtractedDocument" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "fileName" TEXT NOT NULL,
    "rawText" TEXT,
    "extractedJson" JSONB,
    "hba1c" DOUBLE PRECISION,
    "glucose" DOUBLE PRECISION,
    "systolicBp" INTEGER,
    "diastolicBp" INTEGER,
    "cholesterol" DOUBLE PRECISION,
    "uploadedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ExtractedDocument_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RiskAssessment" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "diabetesProbability" DOUBLE PRECISION NOT NULL,
    "cardiacProbability" DOUBLE PRECISION NOT NULL,
    "overallRiskScore" DOUBLE PRECISION NOT NULL,
    "riskTier" TEXT NOT NULL,
    "confidenceScore" DOUBLE PRECISION NOT NULL,
    "generatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RiskAssessment_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "InsurancePlan" (
    "id" SERIAL NOT NULL,
    "insurerName" TEXT NOT NULL,
    "planName" TEXT NOT NULL,
    "planType" "PlanType" NOT NULL,
    "premiumMonthly" DOUBLE PRECISION NOT NULL,
    "coverageLimit" DOUBLE PRECISION,
    "deductible" DOUBLE PRECISION,
    "roomRentLimit" DOUBLE PRECISION,
    "icuCoverage" BOOLEAN,
    "networkHospitalsCount" INTEGER,
    "waitingPeriodMonths" INTEGER,
    "maternityCover" BOOLEAN,
    "dentalCover" BOOLEAN,
    "visionCover" BOOLEAN,
    "criticalIllnessCover" BOOLEAN,
    "ambulanceCover" BOOLEAN,
    "cashlessHospitalization" BOOLEAN,
    "preExistingDiseaseCover" BOOLEAN,
    "diabetesCovered" BOOLEAN,
    "cardiacCovered" BOOLEAN,
    "ayushCover" BOOLEAN,
    "familyFloater" BOOLEAN,
    "wardType" TEXT,
    "copayPercentage" DOUBLE PRECISION,
    "exclusions" TEXT,
    "riskTierSupported" TEXT,

    CONSTRAINT "InsurancePlan_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PlanFilter" (
    "id" SERIAL NOT NULL,
    "planId" INTEGER NOT NULL,
    "wardType" TEXT,
    "hospitalNetworkType" TEXT,
    "roomCategory" TEXT,
    "claimSettlementRatio" DOUBLE PRECISION,
    "ageLimit" INTEGER,
    "geographicCoverage" TEXT,
    "monthlyPremiumRange" TEXT,
    "addOnAvailable" BOOLEAN,

    CONSTRAINT "PlanFilter_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Recommendation" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "planId" INTEGER NOT NULL,
    "riskAssessmentId" INTEGER NOT NULL,
    "suitabilityScore" DOUBLE PRECISION NOT NULL,
    "affordabilityScore" DOUBLE PRECISION NOT NULL,
    "coverageMatchScore" DOUBLE PRECISION NOT NULL,
    "riskAlignmentScore" DOUBLE PRECISION NOT NULL,
    "explanation" TEXT NOT NULL,
    "componentScores" JSONB NOT NULL,
    "recommendedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Recommendation_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ComparisonHistory" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "comparedPlanIds" JSONB NOT NULL,
    "comparedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ComparisonHistory_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Profile_userId_key" ON "Profile"("userId");

-- AddForeignKey
ALTER TABLE "Profile" ADD CONSTRAINT "Profile_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ExtractedDocument" ADD CONSTRAINT "ExtractedDocument_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RiskAssessment" ADD CONSTRAINT "RiskAssessment_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlanFilter" ADD CONSTRAINT "PlanFilter_planId_fkey" FOREIGN KEY ("planId") REFERENCES "InsurancePlan"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Recommendation" ADD CONSTRAINT "Recommendation_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Recommendation" ADD CONSTRAINT "Recommendation_planId_fkey" FOREIGN KEY ("planId") REFERENCES "InsurancePlan"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Recommendation" ADD CONSTRAINT "Recommendation_riskAssessmentId_fkey" FOREIGN KEY ("riskAssessmentId") REFERENCES "RiskAssessment"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ComparisonHistory" ADD CONSTRAINT "ComparisonHistory_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
